"""
clock_in_out.py

This module is used register endpoints to the check-in check-out functionalities
"""

import ipaddress
import logging

import numpy as np
from django.shortcuts import render
from django.apps import apps

from horilla.http.response import HorillaRedirect

logger = logging.getLogger(__name__)
from datetime import date, datetime, timedelta

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from geopy.distance import geodesic

from attendance.methods.utils import (
    activity_datetime,
    employee_exists,
    format_time,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceLateComeEarlyOut,
    GraceTime,
)
from attendance.views.views import attendance_validate
from base.context_processors import (
    enable_late_come_early_out_tracking,
    timerunner_enabled,
)
from base.models import AttendanceAllowedIP, Company, EmployeeShiftDay
from horilla.decorators import hx_request_required, login_required
from horilla.horilla_middlewares import _thread_locals


def _get_request_value(request, key):
    if request.method == "POST" and key in request.POST:
        return request.POST.get(key)
    return request.GET.get(key)


def _is_htmx_request(request):
    return (request.META.get("HTTP_HX_REQUEST") or "").lower() == "true" or (
        request.headers.get("HX-Request", "").lower() == "true"
    )


def _request_is_system_clock(request):
    return bool(getattr(request, "__dict__", {}).get("datetime"))


def _get_employee_company(employee):
    try:
        work_info = getattr(employee, "employee_work_info", None)
        return getattr(work_info, "company_id", None)
    except Exception:
        return None


def _company_has_geofencing_enabled(employee):
    try:
        GeoFencing = apps.get_model("geofencing", "GeoFencing")
    except Exception:
        return False
    company = _get_employee_company(employee)
    if company and hasattr(company, "geo_fencing"):
        try:
            return bool(company.geo_fencing and company.geo_fencing.start)
        except Exception:
            return False
    try:
        global_cfg = GeoFencing.objects.filter(company_id__isnull=True).first()
        return bool(global_cfg and global_cfg.start)
    except Exception:
        return False


def _get_geofencing_config(employee):
    try:
        GeoFencing = apps.get_model("geofencing", "GeoFencing")
    except Exception:
        return None
    company = _get_employee_company(employee)
    if company:
        cfg = GeoFencing.objects.filter(company_id=company).first()
        if cfg:
            return cfg
    return GeoFencing.objects.filter(company_id__isnull=True).first()


def _company_has_face_detection_enabled(employee):
    try:
        FaceDetection = apps.get_model("facedetection", "FaceDetection")
    except Exception:
        return False
    company = _get_employee_company(employee)
    if company:
        cfg = FaceDetection.objects.filter(company_id=company).first()
        if cfg:
            return bool(cfg.start)
    cfg = FaceDetection.objects.filter(company_id__isnull=True).first()
    return bool(cfg and cfg.start)


def _read_uploaded_image(uploaded_file):
    try:
        import cv2
    except Exception:
        return None
    try:
        data = uploaded_file.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None
    finally:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass


def _extract_single_face_gray(image_bgr):
    try:
        import cv2
    except Exception:
        return None
    if image_bgr is None:
        return None
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    if faces is None or len(faces) != 1:
        return None
    x, y, w, h = faces[0]
    face = gray[y : y + h, x : x + w]
    try:
        face = cv2.resize(face, (200, 200))
    except Exception:
        return None
    return face


def _selfie_has_face(selfie):
    image = _read_uploaded_image(selfie)
    return _extract_single_face_gray(image) is not None


def _selfie_matches_employee(selfie, employee):
    try:
        import cv2
    except Exception:
        return False
    try:
        EmployeeFaceDetection = apps.get_model("facedetection", "EmployeeFaceDetection")
    except Exception:
        return False
    ref = EmployeeFaceDetection.objects.filter(employee_id=employee).first()
    if not ref or not getattr(ref, "image", None):
        return True
    selfie_face = _extract_single_face_gray(_read_uploaded_image(selfie))
    if selfie_face is None:
        return False
    try:
        ref_img = cv2.imread(ref.image.path)
    except Exception:
        return False
    ref_face = _extract_single_face_gray(ref_img)
    if ref_face is None:
        return False
    if not hasattr(cv2, "face"):
        return False
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train([ref_face], np.array([0]))
    _, confidence = recognizer.predict(selfie_face)
    return confidence < 80


def _enforce_geofencing_for_request(request, employee):
    if _request_is_system_clock(request) or not _is_htmx_request(request):
        return None
    if not _company_has_geofencing_enabled(employee):
        return None
    lat = _get_request_value(request, "latitude")
    lng = _get_request_value(request, "longitude")
    if not lat or not lng:
        return HttpResponse(_("Geolocation is required to mark attendance."))
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except Exception:
        return HttpResponse(_("Invalid geolocation values."))
    cfg = _get_geofencing_config(employee)
    if not cfg or not cfg.start:
        return None
    distance_m = geodesic((cfg.latitude, cfg.longitude), (lat_f, lng_f)).meters
    if distance_m > cfg.radius_in_meters:
        return HttpResponse(_("You are outside the allowed geofence radius."))
    return None


def _enforce_face_detection_for_request(request, employee):
    if _request_is_system_clock(request) or not _is_htmx_request(request):
        return None
    if not _company_has_face_detection_enabled(employee):
        return None
    try:
        import cv2  # noqa: F401
    except Exception:
        return HttpResponse(_("Face detection server side required opencv instalation"))
    selfie = request.FILES.get("selfie")
    if not selfie:
        return HttpResponse(_("Selfie is required to mark attendance."))
    if not _selfie_has_face(selfie):
        return HttpResponse(_("No valid face detected in the selfie."))
    if not _selfie_matches_employee(selfie, employee):
        return HttpResponse(_("Face verification failed."))
    return None


def late_come_create(attendance):
    """
    used to create late come report
    args:
        attendance : attendance object
    """

    if AttendanceLateComeEarlyOut.objects.filter(
        type="late_come", attendance_id=attendance
    ).exists():
        late_come_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="late_come", attendance_id=attendance
        ).first()
    else:
        late_come_obj = AttendanceLateComeEarlyOut()

    late_come_obj.type = "late_come"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def late_come(attendance, start_time, end_time, shift):
    """
    this method is used to mark the late check-in  attendance after the shift starts
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        end_time : attendance day shift end time

    """
    if not enable_late_come_early_out_tracking(None).get("tracking"):
        return
    request = getattr(_thread_locals, "request", None)
    now_sec = strtime_seconds(attendance.attendance_clock_in.strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")

    # Checking gracetime allowance before creating late come
    if shift and shift.grace_time_id:
        # checking grace time in shift, it has the higher priority
        if (
            shift.grace_time_id.is_active == True
            and shift.grace_time_id.allowed_clock_in == True
        ):
            # Setting allowance for the check in time
            now_sec -= shift.grace_time_id.allowed_time_in_secs
    # checking default grace time
    elif GraceTime.objects.filter(is_default=True, is_active=True).exists():
        grace_time = GraceTime.objects.filter(
            is_default=True,
            is_active=True,
        ).first()
        # Setting allowance for the check in time if grace allocate for clock in event
        if grace_time.allowed_clock_in:
            now_sec -= grace_time.allowed_time_in_secs
    else:
        pass
    if start_time > end_time and start_time != end_time:
        # night shift
        if now_sec < mid_day_sec:
            # Here  attendance or attendance activity for new day night shift
            late_come_create(attendance)
        elif now_sec > start_time:
            # Here  attendance or attendance activity for previous day night shift
            late_come_create(attendance)
    elif start_time < now_sec:
        late_come_create(attendance)
    return True


def clock_in_attendance_and_activity(
    employee,
    date_today,
    attendance_date,
    day,
    now,
    shift,
    minimum_hour,
    start_time,
    end_time,
    in_datetime,
):
    """
    This method is used to create attendance activity or attendance when an employee clocks-in
    args:
        employee        : employee instance
        date_today      : date
        attendance_date : the date that attendance for
        day             : shift day
        now             : current time
        shift           : shift object
        minimum_hour    : minimum hour in shift schedule
        start_time      : start time in shift schedule
        end_time        : end time in shift schedule
    """

    # attendance activity create
    activity = AttendanceActivity.objects.filter(
        employee_id=employee,
        attendance_date=attendance_date,
        clock_in_date=date_today,
        shift_day=day,
        clock_out=None,
    ).first()

    if activity and not activity.clock_out:
        activity.clock_out = in_datetime
        activity.clock_out_date = date_today
        activity.save()

    new_activity = AttendanceActivity.objects.create(
        employee_id=employee,
        attendance_date=attendance_date,
        clock_in_date=date_today,
        shift_day=day,
        clock_in=in_datetime,
        in_datetime=in_datetime,
    )
    # create attendance if not exist
    attendance = Attendance.objects.filter(
        employee_id=employee, attendance_date=attendance_date
    )
    if not attendance.exists():
        attendance = Attendance()
        attendance.employee_id = employee
        attendance.shift_id = shift
        attendance.work_type_id = attendance.employee_id.employee_work_info.work_type_id
        attendance.attendance_date = attendance_date
        attendance.attendance_day = day
        attendance.attendance_clock_in = now
        attendance.attendance_clock_in_date = date_today
        attendance.minimum_hour = minimum_hour
        attendance.save()
        # check here late come or not

        attendance = Attendance.find(attendance.id)
        late_come(
            attendance=attendance, start_time=start_time, end_time=end_time, shift=shift
        )
    else:
        attendance = attendance[0]
        attendance.attendance_clock_out = None
        attendance.attendance_clock_out_date = None
        attendance.save()
        # delete if the attendance marked the early out
        early_out_instance = attendance.late_come_early_out.filter(type="early_out")
        if early_out_instance.exists():
            early_out_instance[0].delete()
    return attendance


@login_required
@hx_request_required
def clock_in(request):
    """
    This method is used to mark the attendance once per a day and multiple attendance activities.
    """
    # check wether check in/check out feature is enabled
    selected_company = request.session.get("selected_company")
    if selected_company == "all":
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=None
        ).first()
    else:
        company = Company.objects.filter(id=selected_company).first()
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=company
        ).first()
    # request.__dict__.get("datetime")' used to check if the request is from a biometric device
    if (
        attendance_general_settings
        and attendance_general_settings.enable_check_in
        or request.__dict__.get("datetime")
    ):
        allowed_attendance_ips = AttendanceAllowedIP.objects.first()

        if (
            not request.__dict__.get("datetime")
            and allowed_attendance_ips
            and allowed_attendance_ips.is_enabled
        ):

            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = request.META.get("REMOTE_ADDR")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]

            allowed_ips = allowed_attendance_ips.additional_data.get("allowed_ips", [])
            ip_allowed = False
            for allowed_ip in allowed_ips:
                try:
                    if ipaddress.ip_address(ip) in ipaddress.ip_network(
                        allowed_ip, strict=False
                    ):
                        ip_allowed = True
                        break
                except ValueError:
                    continue

            if not ip_allowed:
                return HttpResponse(_("You cannot mark attendance from this network"))

        employee, work_info = employee_exists(request)
        datetime_now = timezone.localtime()
        if request.__dict__.get("datetime"):
            datetime_now = request.datetime
        if employee and work_info is not None:
            geofence_block = _enforce_geofencing_for_request(request, employee)
            if geofence_block is not None:
                return geofence_block
            face_block = _enforce_face_detection_for_request(request, employee)
            if face_block is not None:
                return face_block
            selfie = request.FILES.get("selfie")

            shift = work_info.shift_id
            date_today = date.today()
            if request.__dict__.get("date"):
                date_today = request.date
            attendance_date = date_today
            day = date_today.strftime("%A").lower()
            day = EmployeeShiftDay.objects.get(day=day)
            now = datetime.now().strftime("%H:%M")
            if request.__dict__.get("time"):
                now = request.time.strftime("%H:%M")
            now_sec = strtime_seconds(now)
            mid_day_sec = strtime_seconds("12:00")
            minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                day=day, shift=shift
            )
            if start_time_sec > end_time_sec:
                # night shift
                # ------------------
                # Night shift in Horilla consider a 24 hours from noon to next day noon,
                # the shift day taken today if the attendance clocked in after 12 O clock.

                if mid_day_sec > now_sec:
                    # Here you need to create attendance for yesterday

                    date_yesterday = date_today - timedelta(days=1)
                    day_yesterday = date_yesterday.strftime("%A").lower()
                    day_yesterday = EmployeeShiftDay.objects.get(day=day_yesterday)
                    minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                        day=day_yesterday, shift=shift
                    )
                    attendance_date = date_yesterday
                    day = day_yesterday
            attendance = clock_in_attendance_and_activity(
                employee=employee,
                date_today=date_today,
                attendance_date=attendance_date,
                day=day,
                now=now,
                shift=shift,
                minimum_hour=minimum_hour,
                start_time=start_time_sec,
                end_time=end_time_sec,
                in_datetime=datetime_now,
            )
            if selfie:
                try:
                    activity = (
                        AttendanceActivity.objects.filter(employee_id=employee)
                        .order_by("-id")
                        .first()
                    )
                    if activity is not None and hasattr(activity, "clock_in_selfie"):
                        activity.clock_in_selfie = selfie
                        activity.save()
                except Exception:
                    pass

                if _company_has_face_detection_enabled(employee):
                    try:
                        EmployeeFaceDetection = apps.get_model(
                            "facedetection", "EmployeeFaceDetection"
                        )
                        if not EmployeeFaceDetection.objects.filter(
                            employee_id=employee
                        ).exists():
                            EmployeeFaceDetection.objects.create(
                                employee_id=employee, image=selfie
                            )
                    except Exception:
                        pass
            return render(
                request, "attendance/components/in_out_component.html", {"run": 1}
            )
        return HttpResponse(
            _(
                "You Don't have work information filled or your employee detail neither entered "
            )
        )
    else:
        messages.error(request, _("Check in/Check out feature is not enabled."))
        return HorillaRedirect(request)


def clock_out_attendance_and_activity(employee, date_today, now, out_datetime=None):
    """
    Clock out the attendance and activity
    args:
        employee    : employee instance
        date_today  : today date
        now         : now
    """

    attendance_activities = AttendanceActivity.objects.filter(
        employee_id=employee,
    ).order_by("attendance_date", "id")
    attendance_activity = None  # Initialize attendance_activity

    if attendance_activities.filter(clock_out__isnull=True).exists():
        attendance_activity = attendance_activities.filter(
            clock_out__isnull=True
        ).last()
        attendance_activity.clock_out = out_datetime
        attendance_activity.clock_out_date = date_today
        attendance_activity.out_datetime = out_datetime
        attendance_activity.save()

        attendance_activities = attendance_activities.filter(
            attendance_date=attendance_activity.attendance_date
        )
        # Here calculate the total durations between the attendance activities

        duration = 0
        for activity in attendance_activities:
            in_datetime, out_datetime = activity_datetime(activity)
            difference = out_datetime - in_datetime
            days_second = difference.days * 24 * 3600
            seconds = difference.seconds
            total_seconds = days_second + seconds
            duration = duration + total_seconds
        duration = format_time(duration)
        # update clock out of attendance
        attendance = Attendance.objects.filter(employee_id=employee).order_by(
            "-attendance_date", "-id"
        )[0]
        attendance.attendance_clock_out = now + ":00"
        attendance.attendance_clock_out_date = date_today
        attendance.attendance_worked_hour = duration
        # Overtime calculation
        attendance.attendance_overtime = overtime_calculation(attendance)

        # Validate the attendance as per the condition
        attendance.attendance_validated = attendance_validate(attendance)
        attendance.save()

        return attendance

    logger.error("No attendance clock in activity found that needs clocking out.")
    return


def early_out_create(attendance):
    """
    Used to create early out report
    args:
        attendance : attendance obj
    """
    if AttendanceLateComeEarlyOut.objects.filter(
        type="early_out", attendance_id=attendance
    ).exists():
        late_come_obj = AttendanceLateComeEarlyOut.objects.filter(
            type="early_out", attendance_id=attendance
        ).first()
    else:
        late_come_obj = AttendanceLateComeEarlyOut()
    late_come_obj.type = "early_out"
    late_come_obj.attendance_id = attendance
    late_come_obj.employee_id = attendance.employee_id
    late_come_obj.save()
    return late_come_obj


def early_out(attendance, start_time, end_time, shift):
    """
    This method is used to mark the early check-out attendance before the shift ends
    args:
        attendance : attendance obj
        start_time : attendance day shift start time
        start_end : attendance day shift end time
    """
    if not enable_late_come_early_out_tracking(None).get("tracking"):
        return

    clock_out_time = attendance.attendance_clock_out
    if isinstance(clock_out_time, str):
        clock_out_time = datetime.strptime(clock_out_time, "%H:%M:%S")

    now_sec = strtime_seconds(clock_out_time.strftime("%H:%M"))
    mid_day_sec = strtime_seconds("12:00")
    # Checking gracetime allowance before creating early out
    if shift and shift.grace_time_id:
        if (
            shift.grace_time_id.is_active == True
            and shift.grace_time_id.allowed_clock_out == True
        ):
            now_sec += shift.grace_time_id.allowed_time_in_secs
    elif GraceTime.objects.filter(is_default=True, is_active=True).exists():
        grace_time = GraceTime.objects.filter(
            is_default=True,
            is_active=True,
        ).first()
        # Setting allowance for the check out time if grace allocate for clock out event
        if grace_time.allowed_clock_out:
            now_sec += grace_time.allowed_time_in_secs
    else:
        pass
    if start_time > end_time:
        # Early out condition for night shift
        if now_sec < mid_day_sec:
            if now_sec < end_time:
                # Early out condition for general shift
                early_out_create(attendance)
        else:
            early_out_create(attendance)
        return
    if end_time > now_sec:
        early_out_create(attendance)
    return


@login_required
@hx_request_required
def clock_out(request):
    """
    This method is used to set the out date and time for attendance and attendance activity
    """
    # check wether check in/check out feature is enabled
    selected_company = request.session.get("selected_company")
    if selected_company == "all":
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=None
        ).first()
    else:
        company = Company.objects.filter(id=selected_company).first()
        attendance_general_settings = AttendanceGeneralSetting.objects.filter(
            company_id=company
        ).first()
    if (
        attendance_general_settings
        and attendance_general_settings.enable_check_in
        or request.__dict__.get("datetime")
    ):
        datetime_now = timezone.localtime()
        if request.__dict__.get("datetime"):
            datetime_now = request.datetime
        employee, work_info = employee_exists(request)
        if not employee or work_info is None:
            return HttpResponse(
                _("You Don't have work information filled or your employee detail neither entered ")
            )
        geofence_block = _enforce_geofencing_for_request(request, employee)
        if geofence_block is not None:
            return geofence_block
        face_block = _enforce_face_detection_for_request(request, employee)
        if face_block is not None:
            return face_block
        selfie = request.FILES.get("selfie")

        shift = work_info.shift_id
        date_today = date.today()
        if request.__dict__.get("date"):
            date_today = request.date
        day = date_today.strftime("%A").lower()
        day = EmployeeShiftDay.objects.get(day=day)
        attendance = (
            Attendance.objects.filter(employee_id=employee)
            .order_by("id", "attendance_date")
            .last()
        )
        if attendance is not None:
            if not attendance.attendance_day:
                day_name = attendance.attendance_date.strftime("%A").lower()
                attendance.attendance_day = EmployeeShiftDay.objects.get(day=day_name)
                attendance.save(update_fields=["attendance_day"])
            day = attendance.attendance_day
        now = datetime.now().strftime("%H:%M")
        if request.__dict__.get("time"):
            now = request.time.strftime("%H:%M")
        try:
            minimum_hour, start_time_sec, end_time_sec = shift_schedule_today(
                day=day, shift=shift
            )
            attendance = clock_out_attendance_and_activity(
                employee=employee, date_today=date_today, now=now, out_datetime=datetime_now
            )
            if selfie:
                try:
                    activity = (
                        AttendanceActivity.objects.filter(employee_id=employee)
                        .order_by("-id")
                        .first()
                    )
                    if activity is not None and hasattr(activity, "clock_out_selfie"):
                        activity.clock_out_selfie = selfie
                        activity.save()
                except Exception:
                    logger.exception("Failed to store clock-out selfie.")
            if attendance:
                try:
                    early_out_instance = attendance.late_come_early_out.filter(type="early_out")
                    is_night_shift = attendance.is_night_shift()
                    next_date = attendance.attendance_date + timedelta(days=1)
                    if not early_out_instance.exists():
                        if is_night_shift:
                            now_sec = strtime_seconds(now)
                            mid_sec = strtime_seconds("12:00")

                            if (attendance.attendance_date == date_today) or (
                                # check is next day mid
                                mid_sec >= now_sec
                                and date_today == next_date
                            ):
                                early_out(
                                    attendance=attendance,
                                    start_time=start_time_sec,
                                    end_time=end_time_sec,
                                    shift=shift,
                                )
                        elif attendance.attendance_date == date_today:
                            early_out(
                                attendance=attendance,
                                start_time=start_time_sec,
                                end_time=end_time_sec,
                                shift=shift,
                            )
                except Exception:
                    logger.exception("Clock-out succeeded but post-processing failed (early-out).")
        except Exception:
            logger.exception("Clock-out request failed after updating state; returning UI anyway.")

        return render(
            request, "attendance/components/in_out_component.html", {"run": 1}
        )

    else:
        messages.error(request, _("Check in/Check out feature is not enabled."))
        return HorillaRedirect(request)
