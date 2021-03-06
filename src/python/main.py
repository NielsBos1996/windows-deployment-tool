import platform  # To get current platform, use platform.platform()
import sys
import csv
import os
import locale  # Controleren van de OS taal
import ctypes  # Controleren OS taal
import subprocess
import getpass
import logging
import shutil
import time
import threading
import urllib3
import webbrowser

from PyQt5.QtCore import QDateTime, QDate, Qt
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox, \
    QTableWidgetItem, QLabel, QScrollArea
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets, QtGui, QtCore


try:
    os.chdir(os.path.dirname(sys.argv[0]))
except Exception:
    pass

# Set logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.disable(logging.DEBUG)


# Resource path bepalen
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.environ.get("_MEIPASS2", os.path.abspath("."))
    # logging.info('Pyinstaller file location {}'.format(base_path))
    return os.path.join(base_path, relative_path)


# Programm uitvoeren als Administrator
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

current_version = float(1.0)

# Release page
def website_update():
    webbrowser.open('https://github.com/jebr/windows-deployment-tool/releases')

class MainPage(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi(resource_path('../resources/ui/main_window.ui'), self)
        self.setFixedSize(900, 760)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))
        self.actionAbout.triggered.connect(self.open_info_window)
        self.actionLicence.triggered.connect(self.open_license_window)
        self.actionSettings.triggered.connect(self.open_settings_popup)

        # Controleer systeemtaal
        windll = ctypes.windll.kernel32
        windll.GetUserDefaultUILanguage()
        self.os_language = locale.windows_locale[windll.GetUserDefaultUILanguage()]

        # Controleer windows versie
        self.os_version = platform.platform()

        # System checks
        self.pushButton_system_check.clicked.connect(self.system_checks_thread)
        self.pushButton_check_secpol.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_secpol.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_check_rdp.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_rdp.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_usb.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_check_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_check_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_check_windows_updates.clicked.connect(self.open_update)
        self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))

        # Pre-system checks
        self.windows7_check()
        self.usb_check_thread()
        if self.check_update_wdt():  # Check for update WDT
            self.infobox_update(f'v{self.new_version} is nu beschikbaar om te installeren.\n Wil je deze nu downloaden?')
            self.statusBar().showMessage(f'Nieuwe versie beschikbaar v{self.new_version}')
        else:
            self.statusBar().showMessage(f'Windows Deployment Tool v{self.new_version}')

        # Update button
        self.actioncheck_update_wdt.triggered.connect(self.check_update_wdt_button)

        threading.Thread(target=self.energy_check, daemon=True).start()  # Check energy settings

        # Hostname
        self.pushButton_info_hostname.clicked.connect(self.open_hostname_help)
        self.pushButton_info_hostname.setIcon(QIcon(QPixmap(resource_path('../icons/circle-info.png'))))
        self.pushButton_info_hostname.setToolTip('Klik voor informatie over computernaam')
        self.label_hostname.setText('Huidige computernaam: {}'.format(os.getenv('COMPUTERNAME')))
        self.pushButton_set_hostname.clicked.connect(self.set_hostname)

        # Import users
        self.pushButton_import_csv.clicked.connect(self.load_csv_file)
        self.pushButton_users_add.clicked.connect(self.add_windows_users)
        self.pushButton_clear_users_table.clicked.connect(self.clear_users_table)

        # Security policy
        self.pushButton_sec_policy.clicked.connect(self.import_sec_policy_thread)

        # USB-storage
        self.pushButton_usb_enable.clicked.connect(self.enable_usb_thread)
        self.pushButton_usb_disable.clicked.connect(self.disable_usb_thread)

        # Firewall instellingen
        self.pushButton_firewall_ping.clicked.connect(self.firewall_ping_thread)
        self.pushButton_firewall_discovery.clicked.connect(self.firewall_network_discovery_thread)

        # Remote desktop (RDP)
        self.pushButton_rdp_enable.clicked.connect(self.enable_rdp_thread)

        # Energy settings
        self.pushButton_energy_on.clicked.connect(self.enery_on_thread)
        self.pushButton_energy_lock.clicked.connect(self.enery_lock_thread)
        self.pushButton_energy_default.clicked.connect(self.enery_restore_thread)

        # Restart system
        self.pushButton_restart_system.clicked.connect(self.restart_system)

        # Additional data
        datetime = QDateTime.currentDateTime()
        self.dateEdit_date.setDateTime(datetime)

        # Set counter for started threads
        self.counter_threads = 0

    # Button to check on updates
    def check_update_wdt_button(self):
        if self.check_update_wdt():
            self.infobox_update(
                f'v{self.new_version} is nu beschikbaar om te installeren.\n Wil je deze nu downloaden?')
            self.statusBar().showMessage(f'Nieuwe versie beschikbaar v{self.new_version}')
        else:
            self.infobox(f'Je maakt momenteel gebruik van de nieuwste versie (v{current_version})')

    # WDT update check
    def check_update_wdt(self):
        try:
            timeout = urllib3.Timeout(connect=2.0, read=7.0)
            http = urllib3.PoolManager(timeout=timeout)
            response = http.request('GET',
                                    'https://raw.githubusercontent.com/jebr/windows-deployment-tool/master/version.txt')
            data = response.data.decode('utf-8')

            self.new_version = float(data)

            if current_version < self.new_version:
                # logging.info('Current software version: v{}'.format(current_version))
                # logging.info('New software version available v{}'.format(new_version))
                # logging.info('https://github.com/jebr/windows-deployment-tool/releases')
                # self.infobox_update(f'v{self.new_version} is nu beschikbaar om te installeren.\n Wil je deze nu downloaden?')
                # self.statusBar().showMessage(f'Nieuwe versie beschikbaar v{self.new_version}')
                return True
            else:
                # logging.info('Current software version: v{}'.format(current_version))
                # logging.info('Latest release: v{}'.format(new_version))
                # logging.info('Software up-to-date')
                # self.statusBar().showMessage(f'Windows Deployment Tool v{self.new_version}')
                # self.infobox(f'Je maakt momenteel gebruik van de nieuwste versie (v{current_version})')
                return False

        except urllib3.exceptions.MaxRetryError:
            logging.error('No internet connection, max retry error')
        except urllib3.exceptions.ResponseError:
            logging.error('No internet connection, no response error')

    # System checks
    def system_checks(self):
        self.counter_threads = 0
        self.pushButton_system_check.setEnabled(False)
        threading.Thread(target=self.windows_chars, daemon=True).start()
        threading.Thread(target=self.secpol_check, daemon=True).start()
        threading.Thread(target=self.rdp_check, daemon=True).start()
        threading.Thread(target=self.fw_icmp_check, daemon=True).start()
        threading.Thread(target=self.fw_discovery_check, daemon=True).start()
        threading.Thread(target=self.energy_check, daemon=True).start()
        threading.Thread(target=self.get_users, daemon=True).start()
        while True:
            if self.counter_threads == 7:  # Verhogen als er meer threads in deze functie geplaatst worden
                break
            time.sleep(0.05)
        self.pushButton_export_system_settings.setEnabled(True)
        self.pushButton_system_check.setEnabled(True)

    def system_checks_thread(self):
        thread = threading.Thread(target=self.system_checks, daemon=True)
        thread.start()

    def windows7_check(self):
        os_version = platform.platform()
        if "Windows-7" in os_version:
            self.warningbox('Windows 7 wordt niet meer ondersteund')
            sys.exit()

    def energy_check(self):
        energy_on_scheme = '00000000-0000-0000-0000-000000000000'
        energy_lock_scheme = '39ff2e23-e11c-4fc3-ab0f-da25fadb8a89'

        active_scheme = subprocess.check_output(['powershell.exe', 'powercfg /getactivescheme'])
        active_scheme = active_scheme.decode('utf-8')

        if energy_on_scheme in active_scheme:
            self.label_energie_settings.setText('Altijd aan')
            self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            # self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            # self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        elif energy_lock_scheme in active_scheme:
            self.label_energie_settings.setText('Automatisch vergrendelen')
            # self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            # self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        else:
            self.label_energie_settings.setText('Standaard energieplan')
            # self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            # self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
        self.counter_threads += 1

    def secpol_check(self):
        if os.path.exists('c:\\windows\\system32\secpol_new.inf'):
            self.pushButton_check_secpol.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            self.pushButton_secpol.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
        self.counter_threads += 1

    def rdp_check(self):
        self.rdp_register_path = 'Registry::"HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server"'
        self.rdp_reg_dword = "fDenyTSConnections"
        # Controleer de waarde van het register
        self.check_rdp = str(subprocess.check_output(['powershell.exe', 'Get-ItemProperty -Path {} -Name {}'.format(self.rdp_register_path, self.rdp_reg_dword)]))
        if "0" in self.check_rdp:
            self.pushButton_check_rdp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            self.pushButton_rdp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
        self.counter_threads += 1

    def fw_icmp_check(self):
        icmp_rule_nl = str('Get-NetFirewallRule -DisplayName \"Bestands- en printerdeling '
                           '(Echoaanvraag - ICMPv4-In)\" | select DisplayName, Enabled')
        icmp_rule_en = str('Get-NetFirewallRule -DisplayName \"File and Printer Sharing '
                           '(Echo Request - ICMPv4-In)\" | select DisplayName, Enabled')
        if "nl" in self.os_language:
            try:
                check_nl = str(subprocess.check_output(['powershell.exe', icmp_rule_nl]))
                if "True" in check_nl:
                    self.pushButton_check_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                    self.pushButton_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            except Exception as e:
                logging.info('Firewall check failed with error code {}'.format(e))
        elif "en" in self.os_language:
            try:
                check_en = str(subprocess.check_output(['powershell.exe', icmp_rule_en]))
                if "True" in check_en:
                    self.pushButton_check_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                    self.pushButton_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            except Exception as e:
                logging.info('Firewall check failed with error code {}'.format(e))
        self.counter_threads += 1

    def fw_discovery_check(self):
        # Netwerk detecteren (NB-Datagram-In)
        # Network Discovery (NB-Datagram-In)
        if "nl" in self.os_language:
            try:
                check_en = subprocess.check_output(['powershell.exe', 'Get-NetFirewallRule -DisplayName '
                                                                      '"Netwerk detecteren (NB-Datagram-In)"  | '
                                                                      'select DisplayName, Enabled'])
                check_en = check_en.decode('utf-8')
                check_true = check_en.count("True")
                if check_true == 3:
                    self.pushButton_check_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/'
                                                                                           'circle-check.png'))))
                    self.pushButton_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            except Exception as e:
                logging.info(e)
        elif "en" in self.os_language:
            try:
                check_en = subprocess.check_output(['powershell.exe', 'Get-NetFirewallRule -DisplayName '
                                                           '"Network Discovery (NB-Datagram-In)"  | '
                                                           'select DisplayName, Enabled'])
                check_en = check_en.decode('utf-8')
                check_true = check_en.count("True")
                if check_true == 3:
                    self.pushButton_check_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/'
                                                                                           'circle-check.png'))))
                    self.pushButton_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            except Exception as e:
                logging.info(e)
        self.counter_threads += 1

    def windows_chars(self):
        w_version = subprocess.check_output(['powershell.exe', '(Get-WmiObject -class Win32_OperatingSystem).Caption'])
        w_version = w_version.decode('utf-8')
        self.label_windows_version.setText(w_version.rstrip())

        if 'nl' in self.os_language:
            self.label_windows_lang.setText('Nederlands')
        elif 'en' in self.os_language:
            self.label_windows_lang.setText('Engels')
        else:
            self.label_windows_lang.setText(self.os_language)

        # Domain / Workgroup check
        w_domain_workgroup = subprocess.check_output(['powershell.exe', '(Get-WmiObject Win32_ComputerSystem).domain'])
        w_domain_workgroup = w_domain_workgroup.decode('utf-8')
        self.label_domain_workgroup.setText(f'{w_domain_workgroup.rstrip()}')

        # Get Hostname
        self.label_windows_hostname.setText(os.getenv('COMPUTERNAME'))

        # Get Manufacturer and model
        manufacturer = subprocess.check_output(['powershell.exe', '(get-wmiobject Win32_ComputerSystem).manufacturer'])
        manufacturer = manufacturer.decode('utf-8')
        model = subprocess.check_output(['powershell.exe', '(get-wmiobject Win32_ComputerSystem).model'])
        model = model.decode('utf-8')
        self.label_manufacturer_model.setText(f'{manufacturer.rstrip()} / {model.rstrip()}')

        # Get PC Type
        type_number = subprocess.check_output(['powershell.exe', '(get-wmiobject Win32_ComputerSystem).PCSystemTypeEx'])
        type_number = int(type_number.decode('utf-8').rstrip())
        if type_number == 1:
            self.label_type.setText('Desktop')
        elif type_number == 2:
            self.label_type.setText('Mobile / Laptop')
        elif type_number == 3:
            self.label.type.setText('Workstation')
        elif type_number == 4:
            self.label_type.setText('Enterprise Server')
        elif type_number == 5:
            self.label_type.setText('Small Office Server (SOHO)')
        elif type_number == 6:
            self.label_type.setText('Appliance PC')
        elif type_number == 7:
            self.label_type.setText('Performance Server')
        elif type_number == 8:
            self.label_type.setText('Maximum')
        else:
            self.label_type('Onbekend product type')

        # Calculate RAM
        bytes_number = subprocess.check_output(
            ['powershell.exe', '(get-wmiobject Win32_ComputerSystem).totalphysicalmemory'])
        bytes_number = int(bytes_number.decode('utf-8'))
        gb_number = bytes_number / (1024 ** 3)
        gb_number = round(gb_number)
        self.label_physicalmemory.setText(f'{gb_number} GB')

        # Get Processor info
        processor_name = subprocess.check_output(['powershell.exe', '(get-wmiobject Win32_Processor).name']).decode('utf-8')
        self.label_processor.setText(processor_name.rstrip())
        self.label_processor.setToolTip(processor_name.rstrip())
        processor_cores = subprocess.check_output(['powershell.exe', '(get-wmiobject Win32_Processor).NumberOfCores']).decode('utf-8')
        processor_logicalprocessors = subprocess.check_output(['powershell.exe', '(get-wmiobject Win32_Processor).NumberOfLogicalProcessors']).decode('utf-8')
        self.label_cores.setText(f'{processor_cores.rstrip()} cores / {processor_logicalprocessors.rstrip()} logical processors')

        # Get Windows Build and Version
        w_release_id = subprocess.check_output(
            ['powershell.exe', '(Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion").ReleaseID'])
        w_release_id = w_release_id.decode('utf-8')
        w_release_version = subprocess.check_output(
            ['powershell.exe', '(Get-WmiObject Win32_OperatingSystem).Version'])
        w_release_version = w_release_version.decode('utf-8')
        self.label_windows_build.setText(f'{w_release_version.rstrip()} / {w_release_id.rstrip()}')

        self.counter_threads += 1

    def open_update(self):
        try:
            subprocess.check_call(['powershell.exe', 'C:\Windows\System32\control.exe /name Microsoft.WindowsUpdate'])
        except Exception as e:
            logging.info('Openen Windows update is mislukt.')

    def get_users(self):
        w_users = subprocess.check_output(['powershell.exe', 'Get-LocalUser | select name, enabled'])
        w_users = w_users.decode('utf-8')
        w_users_output = w_users.splitlines()
        w_group_admin = subprocess.check_output(['powershell.exe', 'net localgroup administrators'])
        w_group_admin = w_group_admin.decode('utf-8')
        self.tableWidget_active_users.clearContents()
        i = 0
        for user in w_users_output:
            if 'True' in user:
                new_user = user.replace('True', "").replace(" ", "")
                self.tableWidget_active_users.setItem(i, 0, QTableWidgetItem(new_user))
                if new_user in w_group_admin:
                    self.tableWidget_active_users.setItem(i, 1, QTableWidgetItem('Ja'))
                else:
                    self.tableWidget_active_users.setItem(i, 1, QTableWidgetItem('Nee'))
                i += 1
        self.counter_threads += 1

    # Firewall
    def firewall_ping(self):
        if "nl" in self.os_language:
            try:
                subprocess.check_call(['powershell.exe',
                                       'Set-NetFirewallRule -DisplayName \"Bestands- en '
                                       'printerdeling (Echoaanvraag - ICMPv4-In)\" -Profile Any -Enabled True'])
                self.pushButton_check_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                logging.info('ICMP is geactiveerd')
            except subprocess.CalledProcessError:
                self.criticalbox('De firewall instelling is niet uitgevoerd!')
        elif "en" in self.os_language:
            try:
                subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"File and Printer Sharing '
                                                         '(Echo Request - ICMPv4-In)\" -Profile Any -Enabled True'])
                self.pushButton_check_fw_icmp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                logging.info('ICMP is geactiveerd')
            except subprocess.CalledProcessError:
                self.criticalbox('De firewall instelling is niet uitgevoerd!')
        else:
            logging.info('Deze taal wordt niet ondersteund')
            
    def firewall_ping_thread(self):
        thread = threading.Thread(target=self.firewall_ping, daemon=True)
        thread.start()

    def firewall_network_discovery(self):
        if "nl" in self.os_language:
            try:
                subprocess.check_call(['powershell.exe', 'netsh advfirewall firewall '
                                                         'set rule group=”Network Discovery” new enable=Yes'])
                self.pushButton_check_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                logging.info('Discovery is geactiveerd')
            except subprocess.CalledProcessError:
                self.criticalbox('De firewall instelling is niet uitgevoerd!')
        elif "en" in self.os_language:
            try:
                subprocess.check_call(['powershell.exe', 'netsh advfirewall firewall '
                                                         'set rule group=”Network Discovery” new enable=Yes'])
                self.pushButton_check_fw_discovery.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                logging.info('Discovery is geactiveerd')
            except subprocess.CalledProcessError:
                self.criticalbox('De firewall instelling is niet uitgevoerd!')
        else:
            logging.info('Deze taal wordt niet ondersteund')
    
    def firewall_network_discovery_thread(self):
        thread = threading.Thread(target=self.firewall_network_discovery, daemon=True)
        thread.start()

    # Functie voor het wijzigen van de computernaam
    def checkout_hostname(self, hostname):
        if len(hostname) > 15 or len(hostname) < 2:
            return False
        prohobited = '\\/_:*?\"<>|. ,~!@#$%^&\'()}{'
        for elem in prohobited:
            if elem in hostname:
                return False
        if hostname.endswith('-'):
            return False
        alphabet = 'abcdefghijklmnopqtrsuvwxyz1234567890'
        if not (hostname[0] in alphabet or hostname[0] in alphabet.upper()):
            return False
        return True

    def set_hostname(self):
        new_hostname = self.lineEdit_hostname.text()
        if not self.checkout_hostname(new_hostname):
            self.add_text_to_log('{} is geen geldige computernaam'.format(new_hostname))
            self.criticalbox('Ongeldige computernaam, zie info button')
            return
        try:
            subprocess.check_call(['powershell.exe', "Rename-Computer -NewName {}".format(new_hostname)])
            self.add_text_to_log('Computernaam is aangepast naar {}'.format(new_hostname))
            logging.info('De computernaam is aangepast naar: {}'.format(self.lineEdit_hostname.text()))
            self.label_hostname_new.setText('Nieuwe computernaam: {}'.format(new_hostname))
            self.lineEdit_hostname.clear()

        except Exception as e:
            self.criticalbox('De uitvoering is mislukt!')
            self.add_text_to_log(str(e))

    # Security
    def import_sec_policy(self):
        secpol_new = resource_path('\\src\\resources\\security\\secpol_new.inf')
        if not os.path.exists(secpol_new):
            self.criticalbox('Kan secpol_new.inf niet vinden \nFunctie kan niet uitgevoerd worden!')
            logging.info('Kan secpol_new.inf niet vinden, import_sec_policy kan niet uitgevoerd worden')
        else:
            current_user_Desktop = 'c:\\users\\{}\\desktop'.format(getpass.getuser())
            program_cwd = os.getcwd()

            # Backup maken van de huidige security policy
            try:
                os.chdir("c:\\windows\\system32")
                subprocess.check_call(['powershell.exe', 'c:\\windows\\system32\\secedit '
                                                         '/export /cfg backup_secpol.inf /log c:\\windows\\system32\\secpol_backup.log /quiet'])
                logging.info('Backup van default security policy is geslaagd')
                try:
                    shutil.copy('backup_secpol.inf', current_user_Desktop)  # Copy secpol_backup to user desktop
                    logging.info('backup_secpol.inf is verplaatst naar {}'.format(current_user_Desktop))
                except Exception as e:
                    self.criticalbox('Kopieeren van backup_secpol.inf is mislukt')
            except Exception as e:
                logging.info('Het maken van de security policy backup is mislukt!\n Foutmelding {}'.format(str(e)))
            finally:
                os.chdir(program_cwd)

            # Testen op een NL systeem
            try:
                # Copy secpol_new to c:\windows\system32
                shutil.copy(secpol_new, 'c:\\windows\\system32')
                # Import secpol_new policy
                try:
                    subprocess.check_call(['powershell.exe', 'c:\\windows\\system32\\secedit /configure '
                                                             '/db c:\\windows\\system32\\defltbase.sdb /cfg {} '
                                                             '/overwrite /log c:\\windows\\system32\\secpol_import.log '
                                                             '/quiet'.format(secpol_new)])
                    logging.info('Import security policy geslaagd')
                    try:
                        subprocess.check_call(['powershell.exe', 'echo y | gpupdate /force /wait:0'])
                        self.pushButton_check_secpol.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                        # FIXME: Nagaan of de gebruiker uitgelogd moet worden na het aanpassen van de policy of
                        # FIXME: pas na het doorlopen van het programma
                        # try:
                        #     subprocess.check_call(['powershell.exe', 'shutdown -L'])
                        # except Exception as e:
                        #     logging.info(str(e))
                    except Exception as e:
                        logging.info(str(e))
                except Exception as e:
                    logging.info('Importeren van security policy is mislukt. {}'.format(str(e)))
            except Exception as e:
                logging.info('Het kopieeren van {} naar c:\\windows\\system32 is mislukt!\n '
                             'Foutmelding {}'.format(secpol_new, str(e)))

    def import_sec_policy_thread(self):
        thread = threading.Thread(target=self.import_sec_policy, daemon=True)
        thread.start()

    # Functie voor het contoleren van de USB activering
    def usb_check(self):
        self.usb_register_path = "Registry::HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR"
        self.usb_reg_dword = "Start"
        # Controleer de waarde van het register
        self.check_usb = str(subprocess.check_output(['powershell.exe', 'Get-ItemProperty -Path {} -Name {}'.format(self.usb_register_path, self.usb_reg_dword)]))
        # Als de waarde 3 is de USB geactiveerd
        if "3" in self.check_usb:
            self.pushButton_usb_enable.setDisabled(True)
            self.pushButton_usb_disable.setDisabled(False)
            self.pushButton_check_usb_enable.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            self.pushButton_check_usb_disable.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_usb.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
        # Als de waarde 4 is de USB gedeactiveerd
        elif "4" in self.check_usb:
            self.pushButton_usb_disable.setDisabled(True)
            self.pushButton_usb_enable.setDisabled(False)
            self.pushButton_check_usb_enable.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_usb_disable.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            self.pushButton_usb.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
        else:
            return

    def usb_check_thread(self):
        thread = threading.Thread(target=self.usb_check, daemon=True)
        thread.start()

    def enable_usb(self):
        try:
            register = 'reg add HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR /v ' \
                       'Start /t REG_DWORD /d 3 /f'
            subprocess.check_call(register.split(" "))
            # self.infobox('USB-opslagapparaten zijn geactiveerd')
            self.usb_check_thread()
        except subprocess.CalledProcessError:
            self.criticalbox('De uitvoering is mislukt')

    def enable_usb_thread(self):
        thread = threading.Thread(target=self.enable_usb, daemon=True)
        thread.start()

    def disable_usb(self):
        try:
            register = 'reg add HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR /v Start /t REG_DWORD /d 4 /f'
            subprocess.check_call(register.split(" "))
            # self.infobox('USB-opslagapparaten zijn gedeactiveerd')
            self.usb_check_thread()
        except subprocess.CalledProcessError:
            self.criticalbox('De uitvoering is mislukt! \n\n Is het programma uitgevoerd als Administrator?')

    def disable_usb_thread(self):
        thread = threading.Thread(target=self.disable_usb, daemon=True)
        thread.start()

    # Wimndows settings
    def enable_rdp(self):
        if self.rdp_check():
            logging.info('RDP is al geactiveerd op deze computer')
            return
        else:
            if "nl" in self.os_language:
                try:
                    subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"Extern bureaublad - '
                                                             'Gebruikersmodus (TCP-In)\" -Profile Any -Enabled True'])
                    subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"Extern bureaublad - '
                                                             'Gebruikersmodus (UDP-In)\" -Profile Any -Enabled True'])
                    subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"Extern bureaublad - '
                                                             'Schaduw (TCP-In)\" -Profile Any -Enabled True'])
                    logging.info('Firewall instellingen voor RDP zijn geactiveerd')
                except subprocess.CalledProcessError:
                    self.criticalbox('De firewall instellingen voor RDP zijn niet uitgevoerd')
            elif "en" in self.os_language:
                try:
                    subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"Remote Desktop - '
                                                             'User Mode (TCP-In)\" -Profile Any -Enabled True'])
                    subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"Remote Desktop - '
                                                             'User Mode (UDP-In)\" -Profile Any -Enabled True'])
                    subprocess.check_call(['powershell.exe', 'Set-NetFirewallRule -DisplayName \"Remote Desktop - '
                                                             'Shadow (TCP-In)\" -Profile Any -Enabled True'])
                    logging.info('Firewall instellingen voor RDP zijn geactiveerd')
                except subprocess.CalledProcessError:
                    self.criticalbox('De firewall instellingen voor RDP zijn niet uitgevoerd')
            try:
                subprocess.check_call(['powershell.exe', 'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f'])
                subprocess.check_call(['powershell.exe', 'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\" /v SecurityLayer /t REG_DWORD /d 0 /f'])
                subprocess.check_call(['powershell.exe', 'reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp" /v UserAuthentication /t REG_DWORD /d 0 /f'])
                logging.info('De register wijzigingen voor RDP zijn geslaagd')
                self.pushButton_check_rdp.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            except subprocess.CalledProcessError:
                logging.info('De register instellingen voor RDP zijn niet uitgevoerd')
            except Exception as e:
                logging.info(e)

    def enable_rdp_thread(self):
        thread = threading.Thread(target=self.enable_rdp, daemon=True)
        thread.start()

    # Energy Settings
    def energy_on(self):
        energy_config = resource_path('../resources/energy/energy-full.pow')
        energy_on_scheme = '00000000-0000-0000-0000-000000000000'

        scheme_list = subprocess.check_output(['powershell.exe', 'powercfg /list'])
        scheme_list = scheme_list.decode('utf-8')

        active_scheme = subprocess.check_output(['powershell.exe', 'powercfg /getactivescheme'])
        active_scheme = active_scheme.decode('utf-8')

        # Check active scheme
        if energy_on_scheme in active_scheme:
            logging.info('Dit energieplan is al actief')
            self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            return

        if energy_on_scheme in scheme_list:
            try:
                subprocess.check_call(['powershell.exe', 'powercfg /delete {}'.format(energy_on_scheme)])
                logging.info('Oude energieplan verwijderd')
                try:
                    subprocess.check_call(['powershell.exe', 'powercfg -import {} {}'
                                          .format(energy_config, energy_on_scheme)])
                    subprocess.check_call(['powershell.exe', 'powercfg -setactive {}'.format(energy_on_scheme)])
                    self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                    self.pushButton_check_energy_default.setIcon(
                        QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                    self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                    logging.info('Instellen van het energieplan is geslaagd')
                except Exception as e:
                    logging.info('Import energieplan is mislukt.')
            except Exception as e:
                logging.info('Oude energieplan kan niet verwijderd worden')
        else:
            try:
                subprocess.check_call(['powershell.exe', 'powercfg -import {} {}'
                                      .format(energy_config, energy_on_scheme)])
                subprocess.check_call(['powershell.exe', 'powercfg -setactive {}'.format(energy_on_scheme)])
                self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                logging.info('Instellen van het energieplan is geslaagd')
            except Exception as e:
                logging.info('Import energieplan is mislukt.')
                
    def enery_on_thread(self):
        thread = threading.Thread(target=self.energy_on, daemon=True)
        thread.start()

    def energy_lock(self):
        energy_config = resource_path('../resources/energy/energy-auto-lock.pow')
        energy_lock_scheme = '39ff2e23-e11c-4fc3-ab0f-da25fadb8a89'

        scheme_list = subprocess.check_output(['powershell.exe', 'powercfg /list'])
        scheme_list = scheme_list.decode('utf-8')

        active_scheme = subprocess.check_output(['powershell.exe', 'powercfg /getactivescheme'])
        active_scheme = active_scheme.decode('utf-8')

        # Check active scheme
        if energy_lock_scheme in active_scheme:
            self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            logging.info('Dit energieplan is al actief')
            return

        if energy_lock_scheme in scheme_list:
            try:
                subprocess.check_call(['powershell.exe', 'powercfg /delete {}'.format(energy_lock_scheme)])
                logging.info('Oude energieplan verwijderd')
                try:
                    subprocess.check_call(['powershell.exe', 'powercfg -import {} {}'
                                          .format(energy_config, energy_lock_scheme)])
                    subprocess.check_call(['powershell.exe', 'powercfg -setactive {}'.format(energy_lock_scheme)])
                    self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                    self.pushButton_check_energy_default.setIcon(
                        QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                    self.pushButton_check_energy_lock.setIcon(
                        QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                    logging.info('Instellen van het energieplan is geslaagd')
                except Exception as e:
                    logging.info('Import energieplan is mislukt.')
            except Exception as e:
                logging.info('Oude energieplan kan niet verwijderd worden')
        else:
            try:
                subprocess.check_call(['powershell.exe', 'powercfg -import {} {}'
                                      .format(energy_config, energy_lock_scheme)])
                subprocess.check_call(['powershell.exe', 'powercfg -setactive {}'.format(energy_lock_scheme)])
                self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                logging.info('Instellen van het energieplan is geslaagd')
            except Exception as e:
                logging.info('Import energieplan is mislukt.')

    def enery_lock_thread(self):
        thread = threading.Thread(target=self.energy_lock, daemon=True)
        thread.start()

    def energy_restore(self):
        energy_config = resource_path('../resources/energy/energy-default.pow')
        energy_default_scheme = '381b4222-f694-41f0-9685-ff5bb260df2e'

        scheme_list = subprocess.check_output(['powershell.exe', 'powercfg /list'])
        scheme_list = scheme_list.decode('utf-8')

        active_scheme = subprocess.check_output(['powershell.exe', 'powercfg /getactivescheme'])
        active_scheme = active_scheme.decode('utf-8')

        # Check active scheme
        if energy_default_scheme in active_scheme:
            self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
            self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
            logging.info('Dit energieplan is al actief')
            return

        if energy_default_scheme in scheme_list:
            try:
                subprocess.check_call(['powershell.exe', 'powercfg /delete {}'.format(energy_default_scheme)])
                logging.info('Oude energieplan verwijderd')
                try:
                    subprocess.check_call(['powershell.exe', 'powercfg -import {} {}'
                                          .format(energy_config, energy_default_scheme)])
                    subprocess.check_call(['powershell.exe', 'powercfg -setactive {}'.format(energy_default_scheme)])
                    self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                    self.pushButton_check_energy_default.setIcon(
                        QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                    self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                    logging.info('Instellen van het energieplan is geslaagd')
                except Exception as e:
                    logging.info('Import energieplan is mislukt.')
            except Exception as e:
                logging.info('Oude energieplan kan niet verwijderd worden')
        else:
            try:
                subprocess.check_call(['powershell.exe', 'powercfg -import {} {}'
                                      .format(energy_config, energy_default_scheme)])
                subprocess.check_call(['powershell.exe', 'powercfg -setactive {}'.format(energy_default_scheme)])
                self.pushButton_check_energy_on.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                self.pushButton_check_energy_default.setIcon(QIcon(QPixmap(resource_path('../icons/circle-check.png'))))
                self.pushButton_check_energy_lock.setIcon(QIcon(QPixmap(resource_path('../icons/transparent.png'))))
                logging.info('Instellen van het energieplan is geslaagd')
            except Exception as e:
                logging.info('Import energieplan is mislukt.')
    
    def enery_restore_thread(self):
        thread = threading.Thread(target=self.energy_restore, daemon=True)
        thread.start()
    
    # Restart system
    def restart_system(self):
        try:
            subprocess.check_call(['powershell.exe', 'shutdown -r -t 10'])
            self.infobox('Het systeeem zal over 10 seconden herstarten')
        except Exception as e:
            self.warningbox('Door een onbekende fout kan het systeem niet herstart worden')
            logging.info('Systeem kan niet herstart worden. {}'.format(e))

    # Add Local Windows Users
    def load_csv_file(self):
        self.clear_users_table()
        fileName, _ = QFileDialog.getOpenFileName(self,
            "selecteer cvs bestand", "", "csv (*.csv)")
        if not fileName:
            # If window is clicked away
            return
        with open(fileName) as csvfile:
            readCSV = csv.reader(csvfile, delimiter=',')
            # Get the first non empty row number
            for i in range(20):
                if not self.tableWidget_add_users.item(i, 0):
                    break
            # Append the data from cvs to the table
            try:
                for row in readCSV:
                    for j in range(5):
                        if j == 4:
                            if row[j].lower() == 'ja':
                                self.tableWidget_add_users.setItem(i, j, QTableWidgetItem('Ja'))
                            else:
                                self.tableWidget_add_users.setItem(i, j, QTableWidgetItem('Nee'))
                        else:
                            self.tableWidget_add_users.setItem(i,j, QTableWidgetItem(row[j]))
                    i += 1
            except Exception as e:
                self.warningbox('Let op, bestand niet geimporteerd')

    # creating a tw cell (voor functie get_local_users)
    def cell(self, var=""):
        item = QtWidgets.QTableWidgetItem()
        item.setText(var)
        return item

    def get_local_users(self):
        # w_users_full = subprocess.check_output(['powershell.exe', 'Get-LocalUser | select name, enabled, description'])
        w_users = subprocess.check_output(['powershell.exe', '(Get-LocalUser).name']).decode('utf-8').splitlines()
        w_users_enabled = subprocess.check_output(['powershell.exe', '(Get-LocalUser).enabled']).decode('utf-8').splitlines()
        w_users_desc = subprocess.check_output(['powershell.exe', '(Get-LocalUser).description']).decode('utf-8').splitlines()
        w_users_fullname = subprocess.check_output(['powershell.exe', '(get-wmiobject -class Win32_USeraccount).fullname']).decode('utf-8').splitlines()
        w_group_admin = subprocess.check_output(['powershell.exe', 'net localgroup administrators'])
        w_group_admin = w_group_admin.decode('utf-8')
        self.tableWidget_add_users.clearContents()
        i = 0

        # Diable cell voor gevonden gerbuikers
        # item = self.cell("text")
        # item.setFlags(QtCore.Qt.ItemIsEnabled)

        for j in range(len(w_users)):
            user = w_users[j]
            enabled = w_users_enabled[j]
            desc = w_users_desc[j]
            fullname = w_users_fullname[j]
            if enabled == 'False':
                continue
            self.tableWidget_add_users.setItem(i, 0, QTableWidgetItem(user))
            self.tableWidget_add_users.setItem(i, 1, QTableWidgetItem('********'))
            self.tableWidget_add_users.setItem(i, 2, QTableWidgetItem(fullname))
            self.tableWidget_add_users.setItem(i, 3, QTableWidgetItem(desc))
            # execute the line below to every item you need locked
            # self.tableWidget_add_users.setItem(i, 0, item)
            if user in w_group_admin:
                self.tableWidget_add_users.setItem(i, 4, QTableWidgetItem('Ja'))
            else:
                self.tableWidget_add_users.setItem(i, 4, QTableWidgetItem('Nee'))
            self.tableWidget_add_users.setEnabled(False)

            i += 1

    def add_windows_users(self):
        w_users = subprocess.check_output(['powershell.exe', '(Get-LocalUser).name']).decode('utf-8').splitlines()
        w_users = [element.lower() for element in w_users]  # Gebruikers naar lowercase
        for i in range(20):
            empty_fields = []
            try:
                user = self.tableWidget_add_users.item(i, 0).text().lower()
                if not user: raise
            except Exception as e:
                empty_fields.append('Gebruikersnaam')
            try:
                password = self.tableWidget_add_users.item(i, 1).text()
                if not password: raise
            except Exception as e:
                empty_fields.append('Wachtwoord')
            try:
                fullname = self.tableWidget_add_users.item(i, 2).text()
                if not fullname: raise
            except Exception as e:
                empty_fields.append('Volledige naam')
            try:
                desc = self.tableWidget_add_users.item(i, 3).text()
                if not desc: raise
            except Exception as e:
                empty_fields.append('Beschrijving')
            try:
                admin = self.tableWidget_add_users.item(i, 4).text()
                if not admin: raise
            except Exception as e:
                empty_fields.append('Administrator')

            if len(empty_fields) == 5:
                continue

            if empty_fields:
                self.warningbox(f'De volgende velden zijn niet ingevuld in rij {i+1}: ' + ', '.join(empty_fields))
                continue

            # Admin veld Ja/ja en anders nee
            admin = True if admin.lower() == 'ja' else False

            if not self.checkout_username(user):
                self.criticalbox(self.username_fault)
                continue

            # Check of de gebruiker al voorkomt op de computer
            if user.lower() in w_users:
                self.warningbox(f'De gebruiker "{user}" komt al voor op deze computer en kan niet toegevoegd. '
                                f'Verander de gebruikersnaam.')
                return False

            try:
                subprocess.check_call(['powershell.exe', f'net user "{user}" "{password}" /add /active:yes '
                                                         f'/fullname:"{fullname}" /comment:"{desc}" /expires:never /Y'])
                subprocess.check_call(['powershell.exe', f'wmic useraccount where "name=\'{user}\'" set PasswordExpires=False '])
                # subprocess.check_call(['powershell.exe', f'$password = {password} -AsSecureString && New-LocalUser "{user}" -Password $password -Fullname {fullname} -Description {desc}'])
                self.tableWidget_add_users.setItem(i, 0, QTableWidgetItem(''))
                self.tableWidget_add_users.setItem(i, 1, QTableWidgetItem(''))
                self.tableWidget_add_users.setItem(i, 2, QTableWidgetItem(''))
                self.tableWidget_add_users.setItem(i, 3, QTableWidgetItem(''))
                self.tableWidget_add_users.setItem(i, 4, QTableWidgetItem(''))
                if admin == True:
                    try:
                        subprocess.check_call(['powershell.exe', f'Add-LocalGroupMember -Group "Administrators" -Member {user}'])
                    except Exception as e:
                        logging.error(f'Gebruiker {user} kan niet toegevoegd worden aan de groep administrators')
                logging.info(f'De gebruiker {user} is succesvol toegevoegd aan deze computer')
            except Exception as e:
                logging.error(f'Gebruiker {user} kan niet toegevoegd worden {e} ')
            # finally:
            #     self.tableWidget_add_users.clearContents()

    def checkout_username(self, username):
        self.username_fault = ''
        if len(username) > 20:
            self.username_fault = ('De gebruikersnaam bevat teveel karakters. Maximaal 20 karakters toegestaan')
            return False
        prohobited = '\\/:*?\"<>| ,@[];=+'
        # " / \ [ ] : ; | = , + * ? < > @
        for elem in prohobited:
            if elem in username:
                self.username_fault = ('De gebruikersnaam bevat ongeldige tekens.')
                return False
        if username.replace(' ','') == '':
            self.username_fault = ('De gebruikersnaam mag niet uit spaties bestaan.')
            return False
        if username.replace('.','.') == '.':
            self.username_fault = ('De gebruikersnaam mag niet uit punten bestaan.')
            return False
        return True

    def password_check(password, samAccountName: str, displayName: str) -> bool:
        """Password requirements based on
        https://docs.microsoft.com/en-us/windows/security/threat-protection/security-policy-settings/password-must-meet-complexity-requirements
        """
        if samAccountName.lower() in password.lower() and len\
                    (samAccountName) > 3:
            logging.info('accountname in password')
            return False

        splits = ',. \t_+/\\$'
        for split in splits:
            splitted_items = displayName.split(split)
            for elem in splitted_items:
                if len(elem) < 3:
                    continue
                if elem in password:
                    logging.info('part of displayname in password')
                    return False

        if displayName.lower() in password.lower():
            logging.info('displayname in password')
            return False

        if len(password) < 8:
            logging.info('password too short')
            return False

        alphabet = 'abcdefghijklmnopqrstuvwxyz'
        alphabet_up = alphabet.upper()
        special = '~!@#$%^&*_-+=`|\\(){}[]:;"`\'<>,.?/'
        letter = '1234567890'

        categories_in_password = 0
        for category in [alphabet, alphabet_up, special, letter]:
            for char in category:
                if char in password:
                    categories_in_password += 1
                    break
        if categories_in_password < 3:
            logging.info('password not diverse enough')
            return False
        
        return True

    def clear_users_table(self):
        self.tableWidget_add_users.clearContents()

    # Log
    def add_text_to_log(self, text):
        '''Adds text to the log tab. Make sure to end each line with a \n
        '''
        self.textBrowser_log.append(text)
        desktop_loc = os.environ['USERPROFILE'] + '\\Desktop'
        os.path.isdir(desktop_loc)
        with open(desktop_loc + 'wtdlog.txt', 'w') as file:
            file.write(self.textBrowser_log.toPlainText())

    # Messageboxen
    def infobox(self, message):
        buttonReply = QMessageBox.information(self, 'Info', message, QMessageBox.Ok)

    def warningbox(self, message):
        buttonReply = QMessageBox.warning(self, 'Warning', message, QMessageBox.Close)

    def criticalbox(self, message):
        buttonReply = QMessageBox.critical(self, 'Error', message, QMessageBox.Close)

    def question(self, message):
        buttonReply = QMessageBox.question(self, 'Question', message, QMessageBox.Ok)

    def noicon(self, message):
        buttonReply = QMessageBox.noicon(self, '', message, QMessageBox.Ok)

    def open_about_popup(self):
        AboutPopup_ = AboutPopup()
        AboutPopup_.exec_()

    def open_licence_popup(self):
        LicencePopup_ = LicencePopup()
        LicencePopup_.exec_()

    def open_settings_popup(self):
        SettingsPopup_ = SettingsPopup()
        SettingsPopup_.exec_()

    def open_hostname_help(self):
        HostnamePopup_ = HostnamePopup()
        HostnamePopup_.exec_()

    def infobox_update(self, message):
        title = f'Windows Deployment Tool v{current_version}'
        buttonReply = QMessageBox.information(self, title, message, QMessageBox.Yes, QMessageBox.No)
        if buttonReply == QMessageBox.Yes:
            webbrowser.open('https://github.com/jebr/windows-deployment-tool/releases')

    def open_info_window(self):
        info_window_ = InfoWindow()
        info_window_.exec_()

    def open_license_window(self):
        license_window_ = LicenceWindow()
        license_window_.exec_()


def powershell(command):
    return subprocess.check_call(['powershell.exe', command])


class AboutPopup(QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        loadUi(resource_path('../resources/ui/about_popup.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))


class LicencePopup(QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        loadUi(resource_path('../resources/ui/licence_popup.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))


class SettingsPopup(QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        loadUi(resource_path('../resources/ui/settings_popup.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))


class HostnamePopup(QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        self.setFixedSize(600, 400)
        loadUi(resource_path('../resources/ui/hostname_help_popup.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))


class InfoWindow(QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        loadUi(resource_path('../resources/ui/info_dialog.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))
        self.setFixedSize(320, 300)
        # Logo
        self.label_info_logo.setText("")
        self.label_info_logo = QLabel(self)
        info_icon = QPixmap(resource_path('../icons/wdt.ico'))
        info_icon = info_icon.scaledToWidth(40)
        self.label_info_logo.setPixmap(info_icon)
        self.label_info_logo.move(140, 10)
        # Labels
        self.label_info_title.setText(f'Windows Deployment Tool v{current_version}')
        self.label_info_link.setText('<a href="https://github.com/jebr/windows-deployment-tool">GitHub repository</a>')
        self.label_info_link.setOpenExternalLinks(True)
        self.label_info_dev.setText('Developers\nJeroen Brauns / Niels van den Bos')
        self.pushButton_update_check.clicked.connect(website_update)


class LicenceWindow(QDialog):
    def __init__(self):
        super().__init__(None, QtCore.Qt.WindowCloseButtonHint)
        loadUi(resource_path('../resources/ui/license_dialog.ui'), self)
        self.setWindowIcon(QtGui.QIcon(resource_path('../icons/wdt.ico')))
        self.setFixedSize(420, 500)
        # Logo
        self.label_info_logo.setText("")
        self.label_info_logo = QLabel(self)
        info_icon = QPixmap(resource_path('../icons/wdt.ico'))
        info_icon = info_icon.scaledToWidth(40)
        self.label_info_logo.setPixmap(info_icon)
        self.label_info_logo.move(180, 10)
        # Labels
        self.label_info_title.setText(f'Windows Deployment Tool v{current_version}')
        self.label_info_link.setText('<a href="https://github.com/jebr/windows-deployment-tool">GitHub repository</a>')
        self.label_info_link.setOpenExternalLinks(True)
        with open('../../LICENSE') as file:
            license_text = file.read()
        self.plainTextEdit_license.setPlainText(license_text)
        self.plainTextEdit_license.centerCursor()
        self.plainTextEdit_license.centerOnScroll()


def main():
    app = QApplication(sys.argv)
    widget = MainPage()
    widget.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    if is_admin():  # Check admin rights
        main()
    else:
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)