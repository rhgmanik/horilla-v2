# Catatan Pekerjaan (Horilla v2)
Tanggal: 2026-05-16

## Ringkasan
- Menampilkan bendera Indonesia pada dropdown bahasa tanpa menambah asset gambar.
- Membatasi pilihan bahasa yang tampil hanya English dan Bahasa Indonesia.
- Menambahkan addon Indonesia (`horilla_id`) untuk kebutuhan Employee dan Payroll Indonesia (profil identitas, setting periode payroll cutoff, dan kalkulasi PPh21).
- Menambahkan hook minimal di core payroll agar logic Indonesia bisa ditaruh di addon (tanpa patch core besar) dan tetap mudah mengikuti update upstream.
- Memperbaiki flow “Download PDF” payslip agar cepat dan tampilannya konsisten seperti v1 (menggunakan browser print), serta membuka di tab baru.
- Menambahkan pengaturan print agar warna background ikut ter-print (sejauh browser mengizinkan).
- Menambahkan integrasi data Employee Indonesia ke Contract sebagai field read-only (source-of-truth tetap dari modul Indonesia).
- Memperbaiki Payslip Report (Excel) agar kolom allowance/deduction menggunakan judul asli komponen dan menghilangkan “Other Allowances/Deductions”.
- Perbaikan white labelling: nama brand hanya kata pertama, konsisten antara login dan dashboard, serta membuka akses publik untuk icon company agar logo tampil di halaman login.
- Memperbaiki format tampilan angka untuk Bahasa Indonesia agar ribuan memakai titik (.) dan desimal memakai koma (,), termasuk kasus input string seperti `18000,00`.

## Bahasa (i18n)
### 1) Dropdown bahasa: bendera Indonesia
- Implementasi: jika `language.0 == "id"`, icon diganti menjadi `<span>` dengan background merah/putih (CSS linear-gradient).
- File:
  - `/home/v2/horilla/base/templates/base/navbar_components/language_settings.html`
  - `/home/v2/horilla/horilla_theme/templates/base/navbar_components/language_settings.html`

### 2) Hanya tampil 2 bahasa (en + id)
- `LANGUAGES` dibatasi menjadi:
  - `("en", "English")`
  - `("id", "Bahasa Indonesia")`
- Default language: `LANGUAGE_CODE = "en"`
- File:
  - `/home/v2/horilla/horilla/settings/local_settings.py`

## Payslip PDF
### Problem
- Download PDF sangat lambat (lebih dari 1 menit). Dari uji sederhana, bottleneck berasal dari proses PDF engine yang memerlukan waktu lama untuk start/render, bukan dari render HTML Django.

### Keputusan solusi (mengikuti v1)
- Menyamakan perilaku seperti v1: bukan server-side PDF rendering, tetapi membuka halaman HTML payslip lalu memicu `window.print()` agar user “Save as PDF” dari browser.
- Keuntungan:
  - Cepat (tidak menunggu engine server-side).
  - Tampilan mengikuti rendering browser (lebih rapi dan konsisten untuk CSS modern).

### Perubahan flow
- Tombol “Download” pada tab payslip sekarang:
  - membuka tab baru ke `view-payslip-pdf/<id>/?print=1`
  - otomatis memunculkan dialog print
- Endpoint lama `payslip-pdf/<id>/` dialihkan (redirect) ke `view-payslip-pdf/<id>/?print=1` untuk kompatibilitas.

File terkait:
- Tombol download:
  - `/home/v2/horilla/payroll/templates/cbv/payslip/payslip_download_tab.html`
- View:
  - `/home/v2/horilla/payroll/views/views.py`
    - `view_payslip_pdf(...)` menerima query `print=1` dan mengirim flag `auto_print`
    - `payslip_pdf(...)` redirect ke `view-payslip-pdf?...`
- Template:
  - `/home/v2/horilla/payroll/templates/payroll/payslip/payslip_pdf.html`
    - Script auto-print aktif hanya saat `auto_print == True`
    - CSS print ditambah agar warna background tidak hilang saat print

### Catatan print warna (background)
- Warna background saat print sangat bergantung pada setting browser.
- Jika hasil PDF masih tanpa warna, aktifkan opsi browser:
  - Chrome/Edge: Print dialog → “More settings” → centang “Background graphics”.

## Cara cek cepat
### Bahasa
- Buka dropdown bahasa di navbar:
  - Pastikan hanya ada “English” dan “Bahasa Indonesia”.
  - Pastikan “Bahasa Indonesia” menampilkan bendera merah/putih.

### Payslip print/PDF
- Buka detail payslip → klik tombol download:
  - Pastikan terbuka tab baru.
  - Pastikan dialog print muncul otomatis.
  - Pilih “Save as PDF” dan cek layout + warna header row.

### Format angka Indonesia
- Ubah bahasa ke “Bahasa Indonesia”.
- Cek angka di list payslip dan detail payslip:
  - Contoh `18000` harus tampil `18.000,00` (dengan simbol mata uang mengikuti setting payroll).
  - Contoh `1234567.89` harus tampil `1.234.567,89`.

## Addon Indonesia (horilla_id)
Tujuan: memindahkan kebutuhan Indonesia ke app terpisah agar update upstream Horilla tetap mudah (patch core seminimal mungkin via hook).

### Struktur utama
- App: `/home/v2/horilla/horilla_id`
- Dihubungkan lewat:
  - `INSTALLED_APPS` (ditambahkan via `local_settings.py`)
  - URL prefix `id/` (ditambahkan ke `/home/v2/horilla/horilla/urls.py`)

### Employee: Indonesia Profile
- Model: `EmployeeIndonesiaProfile` (OneToOne ke `employee.Employee`)
  - Field: NPWP, NIK, BPJS Kesehatan, BPJS Ketenagakerjaan
  - File: `/home/v2/horilla/horilla_id/models.py`
- UI (tab di employee profile):
  - Registrasi tab via `HorillaIdConfig.ready()` → `EmployeeProfileView.add_tab(...)`
    - File: `/home/v2/horilla/horilla_id/apps.py`
  - View HTMX tab: `/home/v2/horilla/horilla_id/views/employee_profile.py`
  - Template tab: `/home/v2/horilla/horilla_id/templates/horilla_id/tabs/indonesia_tab.html`
  - Form: `/home/v2/horilla/horilla_id/forms.py`
- Admin:
  - Register model: `/home/v2/horilla/horilla_id/admin.py`

### Contract: sinkron nilai dari Employee Indonesia (read-only)
Tujuan: field Indonesia terlihat di Contract untuk kebutuhan reporting dan referensi payroll, tetapi tidak dapat diedit dari Contract (input tetap lewat tab Indonesia di Employee).

- Implementasi:
  - Menambah 4 field read-only pada `ContractForm`:
    - `indonesia_npwp`, `indonesia_nik`, `indonesia_bpjs_kesehatan`, `indonesia_bpjs_ketenagakerjaan`
  - Nilai diambil dari `EmployeeIndonesiaProfile` berdasarkan employee yang dipilih.
- Auto-fill saat memilih employee:
  - Endpoint `contract-info-initial` mengembalikan data Indonesia dan JS `contractInitial()` mengisi field read-only.
- File:
  - Form: `/home/v2/horilla/payroll/forms/forms.py`
  - Endpoint: `/home/v2/horilla/payroll/views/views.py` (`contract_info_initial`)
  - JS: `/home/v2/horilla/payroll/templates/payroll/common/form.html` dan `form_fragment.html`

### Payroll: Setting periode (cutoff) + monthly salary mode
- Model: `PayrollPeriodSetting` (OneToOne ke `base.Company`, atau `company=None` untuk default global)
  - `payroll_period_type`: `calendar_month` / `custom_cutoff`
  - `cutoff_day`: 1–31
  - `monthly_salary_mode`: `prorate_by_calendar_month` / `full_period_as_one_month`
  - File: `/home/v2/horilla/horilla_id/models.py`
- Resolver periode/cutoff + default date range:
  - File: `/home/v2/horilla/horilla_id/payroll/period.py`
  - Hook settings:
    - `HORILLA_PAYROLL_PERIOD_CONTEXT`
    - `HORILLA_PAYSLIP_DEFAULT_DATERANGE`
  - Diset di: `/home/v2/horilla/horilla/settings/local_settings.py`
- UI settings (tanpa admin):
  - Endpoint simpan setting: `/home/v2/horilla/horilla_id/views/payroll.py`
  - HTMX default date fields di modal bulk payslip: `/home/v2/horilla/horilla_id/views/payslip.py`
  - Template fragment date fields: `/home/v2/horilla/horilla_id/templates/horilla_id/payroll/payslip_date_fields.html`
  - Integrasi form pada payroll settings:
    - Theme: `/home/v2/horilla/horilla_theme/templates/payroll/settings/payroll_settings.html`
    - Non-theme: `/home/v2/horilla/payroll/templates/payroll/settings/payroll_settings.html`
  - Template tag helper: `/home/v2/horilla/horilla_id/templatetags/horilla_id_tags.py`

### Payroll: PPh21 Indonesia (TER bulanan + rekonsiliasi tahunan)
- Engine kalkulasi:
  - File: `/home/v2/horilla/horilla_id/payroll/pph21.py`
  - Metode:
    - Bulan selain Desember: TER (Tarif Efektif Rata-rata)
    - Bulan Desember: hitung tahunan Pasal 17, lalu kurangi pajak yang sudah dipotong (YTD)
- Adapter hook untuk payroll core:
  - File: `/home/v2/horilla/horilla_id/payroll/tax.py`
  - Hook setting: `HORILLA_TAX_CALCULATOR` (diset di `local_settings.py`)
- Default Filing Status (PTKP) agar user tidak setup manual:
  - Migration seed: `/home/v2/horilla/horilla_id/migrations/0003_default_indonesia_filing_statuses.py`
  - Kode dibuat: `TK/0..3` dan `K/0..3` (`use_py=True`)

#### Detail perhitungan PPh21 (yang diimplementasikan)
- Perhitungan pajak dipakai sebagai nilai `federal_tax` pada payslip melalui hook `HORILLA_TAX_CALCULATOR`.
- Bulanan (Jan–Nov):
  - `income_for_period = gross_pay - non_taxable_allowances`
  - Rate TER dipilih dari tabel berdasarkan PTKP (TK/K) → `tax_for_period = income_for_period * TER_rate`
- Akhir tahun (periode yang `end_date.month == 12`):
  - Hitung akumulasi setahun:
    - `annual_gross = ytd_gross + income_for_period`
    - `job_expense = min(annual_gross * 5%, 6.000.000)`
    - `net_year = annual_gross - job_expense - ytd_pretax`
    - `pkp = floor_to(net_year - PTKP, rounding_pkp)` (default pembulatan 1.000)
  - Pajak tahunan: tarif progresif Pasal 17
  - Rekonsiliasi Desember: `tax_for_period = annual_tax - ytd_tax_withheld`
- Akumulasi YTD (untuk rekonsiliasi):
  - Diambil dari payslip yang sudah terbit di tahun yang sama sebelum periode berjalan:
    - `ytd_tax_withheld` dari `pay_head_data.federal_tax`
    - `ytd_gross` dari `gross_pay - non_taxable_allowances`
    - `ytd_pretax` dari item `pretax_deductions` yang `is_pretax=True`
- Aturan tanpa NPWP:
  - Jika `EmployeeIndonesiaProfile.npwp` kosong, pajak periode dikalikan `no_npwp_multiplier` (default `1.2` → +20%).
  - Konfigurasi default ada di `DEFAULT_CONFIG` dan bisa dioverride lewat `FilingStatus.python_code` (di-parse via `ast.literal_eval`).

## Payslip Report (Excel)
Tujuan: memperjelas report payroll agar allowance/deduction tampil dengan judul aslinya (mis. “Tunjangan Sekolah”, “BPJS Kesehatan”) dan tidak menimbulkan ambiguitas.

- Endpoint:
  - Report: `/payroll/payslip-detailed-export/` → `payslip_detailed_export`
- Perubahan:
  - Header allowance/deduction sekarang dibentuk dari title yang benar-benar muncul pada `Payslip.pay_head_data` hasil filter (bukan dari master table Allowance/Deduction).
  - Kolom “Other Allowances” dan “Other Deductions” dihapus agar tidak ambigu.
- File:
  - `/home/v2/horilla/payroll/views/component_views.py`

## Patch core (minimal hook untuk addon)
Tujuan: memberi “extension point” supaya logic Indonesia berada di addon.

- Hook kalkulator pajak:
  - File: `/home/v2/horilla/payroll/methods/tax_calc.py`
  - Setting: `HORILLA_TAX_CALCULATOR`
- Hook payroll period context + monthly computation fix:
  - File: `/home/v2/horilla/payroll/methods/methods.py`
  - Setting: `HORILLA_PAYROLL_PERIOD_CONTEXT`
- Default date range bulk payslip:
  - File: `/home/v2/horilla/payroll/forms/component_forms.py`
  - Setting: `HORILLA_PAYSLIP_DEFAULT_DATERANGE`

## Migrasi / database
- Addon `horilla_id`:
  - `/home/v2/horilla/horilla_id/migrations/0001_initial.py` (EmployeeIndonesiaProfile)
  - `/home/v2/horilla/horilla_id/migrations/0002_payrollperiodsetting.py` (PayrollPeriodSetting)
  - `/home/v2/horilla/horilla_id/migrations/0003_default_indonesia_filing_statuses.py` (seed FilingStatus PTKP)

## White Labelling
Tujuan: branding aplikasi mengikuti company HQ (white labelling) secara konsisten di login dan dashboard.

- Sumber data white labelling:
  - Context processor: `/home/v2/horilla/base/context_processors.py` (`white_labelling_company`)
  - Variable template:
    - `white_label_company_name` (sudah diubah agar hanya kata pertama via `split()[0]`)
    - `white_label_company` (object company HQ)
- Konsistensi dashboard:
  - Breadcrumbs yang tersimpan di session disinkronkan agar nama brand tidak “nyangkut” dari session lama.
  - File: `/home/v2/horilla/horilla_crumbs/context_processors.py`
  - Sidebar (nav) ditampilkan mengikuti `white_label_company` saat white labelling aktif.
  - File: `/home/v2/horilla/templates/sidebar.html`
- Login page:
  - `login.html` diperbaiki agar atribut `img src` valid dan menggunakan icon `white_label_company.icon` jika tersedia.
  - File: `/home/v2/horilla/templates/login.html`
  - Theme login: judul “Welcome to … HR” diganti menjadi hanya `{{ white_label_company_name }}`.
  - File: `/home/v2/horilla/horilla_theme/templates/login.html`
- Akses logo sebelum login:
  - `/media/` diproteksi lewat `protected_media`, sehingga icon company sebelumnya ter-redirect ke login.
  - Folder `base/company/icon/` ditambahkan ke `exempted_folders` agar icon company bisa diakses publik (khusus untuk kebutuhan login/branding).
  - File: `/home/v2/horilla/base/views.py` (`protected_media`)

## Format Angka (Bahasa Indonesia)
Tujuan: memastikan angka pada payslip/report UI mengikuti format Indonesia:
- Ribuan: tanda titik (`.`)
- Desimal: tanda koma (`,`)

Implementasi:
- Semua tampilan angka yang memakai filter `currency_symbol_position` akan mengikuti format bahasa aktif.
- Jika bahasa aktif dimulai dengan `id`, angka dipaksa menggunakan grouping ribuan lalu separator ditukar menjadi format Indonesia.
- Parsing string angka dibuat lebih robust untuk input yang sudah terformat (mis. hasil `floatformat`) agar tidak fallback ke string mentah (contoh kasus `18000,00`).

File:
- `/home/v2/horilla/base/templatetags/horillafilters.py` (`currency_symbol_position`)
