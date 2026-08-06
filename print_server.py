import http.server
import ctypes
import json

class PrintHandler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == '/print':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Format JSON to Receipt Text
            try:
                data = json.loads(post_data)
                
                lines = []
                # Add 2 blank lines at the top to prevent top line cut-off under the cutter bar
                lines.append("")
                lines.append("")
                
                store_name = data.get('store_name') or data.get('company_name') or data.get('chekNomi') or ''
                store_name_str = str(store_name).strip()
                if not store_name_str or store_name_str.lower() in ('noma\'lum', 'nomalum', 'null', 'none', ''):
                    store_name_str = 'Best Metall'
                lines.append(f"{store_name_str:^40}")
                
                store_phone = data.get('store_phone') or data.get('telefon') or data.get('biznes_telefon') or data.get('phone') or ''
                store_phone_str = str(store_phone).strip()
                if not store_phone_str or store_phone_str.lower() in ('noma\'lum', 'nomalum', 'null', 'none', ''):
                    store_phone_str = '+998905897300'
                lines.append(f"{store_phone_str:^40}")
                lines.append("=" * 40)
                
                sana = data.get('sana') or ''
                sana_str = str(sana).strip()
                chek_no = data.get('check_number') or data.get('kod') or ''
                chek_no_str = str(chek_no).strip()
                
                # Format date and check number safely to dynamically pad up to 40 characters
                prefix = f"Sana: {sana_str}"
                suffix = f"Chek: {chek_no_str}"
                spaces = 40 - len(prefix) - len(suffix)
                if spaces < 1:
                    spaces = 1
                lines.append(prefix + " " * spaces + suffix)
                
                sotuvchi = data.get('sotuvchi') or data.get('kassir')
                xodim = data.get('xodim')
                if not sotuvchi and isinstance(xodim, dict):
                    sotuvchi = xodim.get('nomi')
                sotuvchi_str = str(sotuvchi or '').strip()
                import re
                sotuvchi_str = re.sub(r'\b(foydalanuvchi|user)\b', '', sotuvchi_str, flags=re.IGNORECASE)
                sotuvchi_str = re.sub(r'\s+', ' ', sotuvchi_str).strip()
                lines.append(f"Sotuvchi: {sotuvchi_str}")
                
                mijoz = data.get('mijoz', 'Umumiy mijoz')
                if isinstance(mijoz, dict):
                    mijoz = mijoz.get('nomi', 'Umumiy mijoz')
                mijoz_str = str(mijoz or 'Umumiy mijoz').strip()
                lines.append(f"Mijoz: {mijoz_str}")
                lines.append("-" * 40)
                
                items = data.get('items') or data.get('elementlar') or []
                if not isinstance(items, list):
                    items = []
                    
                for idx, item in enumerate(items, 1):
                    if not isinstance(item, dict):
                        continue
                    no = item.get('no') or idx
                    name = item.get('name') or item.get('nomi') or ''
                    qty = item.get('quantity') or item.get('miqdori') or 0
                    price = item.get('price') or item.get('sotish_narxi') or 0
                    try:
                        qty_f = float(qty)
                        price_f = float(price)
                        item_total = qty_f * price_f
                        qty_str = f"{qty_f:.3f}".rstrip('0').rstrip('.')
                        price_str = f"{price_f:,.0f}".replace(',', ' ')
                        total_str = f"{item_total:,.0f}".replace(',', ' ')
                    except Exception:
                        qty_str = str(qty)
                        price_str = str(price)
                        total_str = str(item.get('total') or item.get('jami_summa') or '')
                    
                    lines.append(f"{no}. {name}")
                    lines.append(f"   {qty_str} * {price_str} = {total_str}")
                    
                lines.append("=" * 40)
                
                total_val = data.get('total') or data.get('yakuniy_summa') or 0
                tolangan_val = data.get('tolangan_summa') or 0
                nasiya_val = data.get('nasiya_summa') or 0
                
                try:
                    total_f = float(total_val)
                except Exception:
                    total_f = 0.0
                try:
                    tolangan_f = float(tolangan_val)
                except Exception:
                    tolangan_f = 0.0
                try:
                    nasiya_f = float(nasiya_val)
                except Exception:
                    nasiya_f = 0.0
                    
                sale_debt = max(0.0, total_f - tolangan_f)
                if sale_debt <= 0.0 and nasiya_f > 0.0:
                    sale_debt = nasiya_f
                
                try:
                    total_formatted = f"{total_f:,.0f}".replace(',', ' ')
                except Exception:
                    total_formatted = str(total_val)
                
                # Format SAVDO dynamically to 40 characters
                prefix = "SAVDO:"
                suffix = total_formatted
                spaces = 40 - len(prefix) - len(suffix)
                if spaces < 1:
                    spaces = 1
                lines.append(prefix + " " * spaces + suffix)
                
                # Payment method breakdown
                payments = data.get('payments', [])
                if not isinstance(payments, list):
                    payments = []
                    
                if not payments:
                    tolov_usuli = data.get('tolov_usuli', '')
                    eslatma = data.get('eslatma', '')
                    
                    if tolov_usuli == 'aralash' and eslatma:
                        import re
                        cleaned_eslatma = re.sub(r'\s+', '', eslatma)
                        naqd_match = re.search(r'(?:Naqd|Cash|Нақд|Накд)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
                        karta_match = re.search(r'(?:Plastikkarta|Plastik|Karta|Card|Uzcard|Humo|Пластик|Карта)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
                        nasiya_match = re.search(r'(?:Nasiya|Qarz|Credit|Насия|Қарз|Карз)\(?(\d+)\)?', cleaned_eslatma, re.IGNORECASE)
                        
                        p_naqd = float(naqd_match.group(1)) if naqd_match else 0.0
                        p_karta = float(karta_match.group(1)) if karta_match else 0.0
                        p_nasiya = float(nasiya_match.group(1)) if nasiya_match else 0.0
                        
                        if p_naqd > 0:
                            payments.append({'name': 'Naqd pul', 'amount': p_naqd})
                        if p_karta > 0:
                            payments.append({'name': 'Plastik karta', 'amount': p_karta})
                        if p_nasiya > 0:
                            payments.append({'name': 'Nasiya', 'amount': p_nasiya})
                    else:
                        if tolov_usuli == 'naqd':
                            payments.append({'name': 'Naqd pul', 'amount': tolangan_f})
                        elif tolov_usuli == 'karta':
                            payments.append({'name': 'Plastik karta', 'amount': tolangan_f})
                        elif tolov_usuli == 'nasiya':
                            payments.append({'name': 'Nasiya', 'amount': nasiya_f})
                        else:
                            if tolangan_f > 0:
                                payments.append({'name': 'Naqd pul', 'amount': tolangan_f})
                            if nasiya_f > 0:
                                payments.append({'name': 'Nasiya', 'amount': nasiya_f})
                
                for payment in payments:
                    if not isinstance(payment, dict):
                        continue
                    p_name = str(payment.get('name') or '').strip()
                    p_amount = payment.get('amount', 0)
                    try:
                        p_amount_f = float(p_amount)
                        p_amount_str = f"{p_amount_f:,.0f}".replace(',', ' ')
                        suffix = f"{p_amount_str} UZS"
                    except Exception:
                        suffix = str(p_amount)
                    
                    prefix = f"{p_name}:"
                    spaces = 40 - len(prefix) - len(suffix)
                    if spaces < 1:
                        spaces = 1
                    lines.append(prefix + " " * spaces + suffix)
                
                # Debt from this sale
                if sale_debt > 0:
                    try:
                        sale_debt_str = f"{sale_debt:,.0f}".replace(',', ' ')
                        suffix = f"{sale_debt_str} UZS"
                    except Exception:
                        suffix = f"{sale_debt} UZS"
                    
                    prefix = "Savdodan qarz:"
                    spaces = 40 - len(prefix) - len(suffix)
                    if spaces < 1:
                        spaces = 1
                    lines.append(prefix + " " * spaces + suffix)
                
                # Total accumulated client debt
                mijoz_new_debt = data.get('mijoz_new_debt')
                if mijoz_new_debt is None and isinstance(data.get('mijoz'), dict):
                    mijoz_new_debt = data.get('mijoz', {}).get('savdodan_sung_qarz') or data.get('mijoz', {}).get('qarz_summasi')
                
                if mijoz_new_debt is not None and mijoz_new_debt != 'null' and mijoz_new_debt != '':
                    try:
                        debt_f = float(mijoz_new_debt)
                        if debt_f > 0:
                            debt_formatted = f"{debt_f:,.0f}".replace(',', ' ')
                            suffix = f"{debt_formatted} UZS"
                            prefix = "Umumiy qarz:"
                            spaces = 40 - len(prefix) - len(suffix)
                            if spaces < 1:
                                spaces = 1
                            lines.append(prefix + " " * spaces + suffix)
                    except Exception:
                        try:
                            # Try simple check if non-zero string
                            if float(mijoz_new_debt) > 0:
                                suffix = f"{mijoz_new_debt} UZS"
                                prefix = "Umumiy qarz:"
                                spaces = 40 - len(prefix) - len(suffix)
                                if spaces < 1:
                                    spaces = 1
                                lines.append(prefix + " " * spaces + suffix)
                        except Exception:
                            pass
                
                # Add 12 feed lines at the bottom for driver auto-cut
                lines.append("\n" * 12)
                receipt_text = "\n".join(lines)
            except Exception as e:
                print("Formatting receipt failed:", e)
                receipt_text = post_data + "\n" * 12

            success = False
            try:
                winspool = ctypes.windll.LoadLibrary('winspool.drv')
                hPrinter = ctypes.c_void_p()
                
                # 1. Check printer_name from request payload, default to POS-80
                printer_name = data.get('printer_name') or 'POS-80'
                if not winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None):
                    # 2. Fallback to default system printer
                    buf_size = ctypes.c_ulong(0)
                    winspool.GetDefaultPrinterW(None, ctypes.byref(buf_size))
                    if buf_size.value > 0:
                        buf = ctypes.create_unicode_buffer(buf_size.value)
                        if winspool.GetDefaultPrinterW(buf, ctypes.byref(buf_size)):
                            printer_name = buf.value
                            winspool.OpenPrinterW(printer_name, ctypes.byref(hPrinter), None)

                # 3. Fallback: enumerate all connected printers if still not opened
                if not hPrinter.value:
                    PRINTER_ENUM_LOCAL = 0x00000002
                    PRINTER_ENUM_CONNECTIONS = 0x00000004
                    cbNeeded = ctypes.c_ulong(0)
                    cReturned = ctypes.c_ulong(0)
                    winspool.EnumPrintersW(PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS, None, 2, None, 0, ctypes.byref(cbNeeded), ctypes.byref(cReturned))
                    if cbNeeded.value > 0:
                        pPrinterEnum = ctypes.create_string_buffer(cbNeeded.value)
                        if winspool.EnumPrintersW(PRINTER_ENUM_LOCAL | PRINTER_ENUM_CONNECTIONS, None, 2, pPrinterEnum, cbNeeded.value, ctypes.byref(cbNeeded), ctypes.byref(cReturned)):
                            class PRINTER_INFO_2W(ctypes.Structure):
                                _fields_ = [
                                    ('pServerName', ctypes.c_wchar_p),
                                    ('pPrinterName', ctypes.c_wchar_p),
                                    ('pShareName', ctypes.c_wchar_p),
                                    ('pPortName', ctypes.c_wchar_p),
                                    ('pDriverName', ctypes.c_wchar_p),
                                    ('pComment', ctypes.c_wchar_p),
                                    ('pLocation', ctypes.c_wchar_p),
                                    ('pDevMode', ctypes.c_void_p),
                                    ('pSepFile', ctypes.c_wchar_p),
                                    ('pPrintProcessor', ctypes.c_wchar_p),
                                    ('pDatatype', ctypes.c_wchar_p),
                                    ('pParameters', ctypes.c_wchar_p),
                                    ('pSecurityDescriptor', ctypes.c_void_p),
                                    ('Attributes', ctypes.c_ulong),
                                    ('Priority', ctypes.c_ulong),
                                    ('DefaultPriority', ctypes.c_ulong),
                                    ('StartTime', ctypes.c_ulong),
                                    ('UntilTime', ctypes.c_ulong),
                                    ('Status', ctypes.c_ulong),
                                    ('cJobs', ctypes.c_ulong),
                                    ('AveragePPM', ctypes.c_ulong),
                                ]
                            printers = ctypes.cast(pPrinterEnum, ctypes.POINTER(PRINTER_INFO_2W))
                            for i in range(cReturned.value):
                                p_info = printers[i]
                                p_name = p_info.pPrinterName
                                if p_name and winspool.OpenPrinterW(p_name, ctypes.byref(hPrinter), None):
                                    printer_name = p_name
                                    break
                
                if hPrinter.value:
                    try:
                        class DOC_INFO_1(ctypes.Structure):
                            _fields_ = [
                                ('pDocName', ctypes.c_wchar_p),
                                ('pOutputFile', ctypes.c_wchar_p),
                                ('pDatatype', ctypes.c_wchar_p)
                            ]
                        doc_info = DOC_INFO_1()
                        doc_info.pDocName = 'Thermal Receipt'
                        doc_info.pOutputFile = None
                        doc_info.pDatatype = 'RAW'

                        if winspool.StartDocPrinterW(hPrinter, 1, ctypes.byref(doc_info)) > 0:
                            try:
                                if winspool.StartPagePrinter(hPrinter):
                                    try:
                                        raw_bytes = receipt_text.encode('utf-8')
                                        bytes_written = ctypes.c_ulong()
                                        winspool.WritePrinter(hPrinter, raw_bytes, len(raw_bytes), ctypes.byref(bytes_written))
                                        success = True
                                    finally:
                                        winspool.EndPagePrinter(hPrinter)
                            finally:
                                winspool.EndDocPrinter(hPrinter)
                    finally:
                        winspool.ClosePrinter(hPrinter)
            except Exception as e:
                print("Direct print failed:", e)

            # Always send 200 to prevent browser printing window popup fallback
            self.send_response(200)
        else:
            self.send_response(404)
            success = False
            
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b"Success" if success else b"Failed")

if __name__ == '__main__':
    server = http.server.HTTPServer(('127.0.0.1', 5000), PrintHandler)
    print("Print server running on port 5000...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down print server.")
