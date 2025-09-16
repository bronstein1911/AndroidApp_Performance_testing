import time
import subprocess
import json
import logging
import threading
from datetime import datetime
import os

# настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    def __init__(self, package_name='com.app'):
        self.package_name = package_name
        self.metrics = {
            'startup_time': 0,
            'screen_transitions': [],
            'memory_usage': [],
            'cpu_usage': [],
            'errors': []
        }
        self.start_time = None
        self.monitoring = False
        self.monitor_thread = None
        
        # проверяем adb при инициализации
        if not self._check_adb_connection():
            raise RuntimeError("adb не подключен или устройство недоступно")
        
    def _check_adb_connection(self):
        """проверяем подключение adb"""
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # пропускаем заголовок
                connected_devices = [line for line in lines if line.strip() and 'device' in line]
                if connected_devices:
                    logger.info(f"найдено устройств: {len(connected_devices)}")
                    return True
                else:
                    logger.error("нет подключенных устройств")
                    return False
        except Exception as e:
            logger.error(f"ошибка проверки adb: {e}")
            return False
        
    def start_monitoring(self):
        self.start_time = time.time()
        self.monitoring = True
        logger.info("начинаем мониторинг производительности")
        
        # запускаем фоновый мониторинг ресурсов
        self.monitor_thread = threading.Thread(target=self._background_monitoring)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        self.monitoring = False
        logger.info("останавливаем мониторинг")
        
        # ждем завершения потока
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                logger.warning("поток мониторинга не остановился за 5 секунд")
        
    def _background_monitoring(self):
        """фоновый мониторинг памяти и CPU"""
        while self.monitoring:
            try:
                memory = self.get_app_memory_usage()
                cpu = self.get_app_cpu_usage()
                
                # детальное логирование при высоких значениях
                if cpu > 20:
                    self._log_high_cpu_usage(cpu)
                if memory > 200:
                    self._log_high_memory_usage(memory)
                
                self.record_memory_usage(memory)
                self.record_cpu_usage(cpu)
                
                time.sleep(2)  # каждые 2 секунды
            except Exception as e:
                logger.error(f"ошибка фонового мониторинга: {e}")
                time.sleep(5)
        
    def _log_high_cpu_usage(self, cpu_value):
        """логирование деталей при высоком CPU"""
        logger.warning(f"высокий CPU: {cpu_value:.1f}%")
        
        try:
            # получаем детальную информацию о процессах
            result = subprocess.run(
                ['adb', 'shell', 'ps', '-A', '-o', 'PID,NAME,CPU,VSZ,RSS'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if self.package_name in line or 'camera' in line.lower() or 'snap' in line.lower():
                        logger.warning(f"   процесс: {line.strip()}")
            
            # получаем активную активность
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'activity', 'activities', '|', 'grep', 'mResumedActivity'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.warning(f"   активная активность: {result.stdout.strip()}")
                
        except Exception as e:
            logger.error(f"ошибка получения деталей CPU: {e}")
    
    def _log_high_memory_usage(self, memory_value):
        """логирование деталей при высоком использовании памяти"""
        logger.warning(f"высокое использование памяти: {memory_value:.1f}МБ")
        
        try:
            # получаем детальную информацию о памяти
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'meminfo', self.package_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if any(keyword in line for keyword in ['TOTAL', 'Java Heap', 'Native Heap', 'Graphics', 'Stack']):
                        logger.warning(f"   память: {line.strip()}")
            
            # получаем информацию о heap
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'meminfo', self.package_name, '|', 'grep', 'Heap'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0 and result.stdout.strip():
                logger.warning(f"   heap: {result.stdout.strip()}")
                
        except Exception as e:
            logger.error(f"ошибка получения деталей памяти: {e}")
    
    def _log_system_state(self):
        """логирование общего состояния системы"""
        try:
            # общая загрузка CPU
            result = subprocess.run(
                ['adb', 'shell', 'top', '-n', '1', '|', 'head', '-10'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'CPU:' in line or 'Load average:' in line:
                        logger.info(f"   система: {line.strip()}")
            
            # свободная память
            result = subprocess.run(
                ['adb', 'shell', 'cat', '/proc/meminfo', '|', 'head', '-5'],
                capture_output=True, text=True, shell=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'MemTotal:' in line or 'MemAvailable:' in line:
                        logger.info(f"   память системы: {line.strip()}")
                        
        except Exception as e:
            logger.error(f"ошибка получения состояния системы: {e}")
        
    def record_screen_transition(self, screen_name, transition_time):
        self.metrics['screen_transitions'].append({
            'screen': screen_name,
            'time': transition_time,
            'timestamp': datetime.now().isoformat()
        })
        logger.info(f"переход на {screen_name}: {transition_time:.2f}с")
        
    def record_memory_usage(self, memory):
        """записываем использование памяти"""
        self.metrics['memory_usage'].append({
            'timestamp': datetime.now().isoformat(),
            'value': memory
        })
    
    def record_cpu_usage(self, cpu):
        """записываем использование CPU"""
        self.metrics['cpu_usage'].append({
            'timestamp': datetime.now().isoformat(),
            'value': cpu
        })
        
    def record_error(self, error_info):
        self.metrics['errors'].append({
            'error': error_info,
            'timestamp': datetime.now().isoformat()
        })
        logger.error(f"ошибка: {error_info}")
        
    def get_app_memory_usage(self):
        try:
            result = subprocess.run(
                ['adb', 'shell', 'dumpsys', 'meminfo', self.package_name],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'TOTAL' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                memory_mb = int(parts[1]) / 1024  # конвертируем в МБ
                                if memory_mb > 0 and memory_mb < 10000:  # валидация
                                    return memory_mb
                                else:
                                    logger.warning(f"подозрительное значение памяти: {memory_mb} МБ")
                                    return 0
                            except ValueError:
                                logger.error(f"не удалось парсить значение памяти: {parts[1]}")
                                return 0
        except Exception as e:
            logger.error(f"ошибка получения памяти: {e}")
        return 0
        
    def get_app_cpu_usage(self):
        try:
            # сначала получаем PID приложения
            result = subprocess.run(
                ['adb', 'shell', 'pidof', self.package_name],
                capture_output=True, text=True
            )
            if result.returncode != 0 or not result.stdout.strip():
                logger.warning(f"приложение {self.package_name} не запущено")
                return 0
                
            pid = result.stdout.strip()
            
            # получаем CPU для конкретного PID
            result = subprocess.run(
                ['adb', 'shell', 'top', '-n', '1', '-p', pid],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if self.package_name in line and not line.startswith('PID'):
                        parts = line.split()
                        if len(parts) >= 9:
                            try:
                                cpu_value = float(parts[8])
                                if 0 <= cpu_value <= 100:  # валидация
                                    return cpu_value
                                else:
                                    logger.warning(f"подозрительное значение CPU: {cpu_value}%")
                                    return 0
                            except ValueError:
                                # пропускаем строки с заголовками
                                continue
        except Exception as e:
            logger.error(f"ошибка получения CPU: {e}")
        return 0
        
    def save_metrics(self, filename=None):
        if not filename:
            filename = f"performance_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        logger.info(f"метрики сохранены в {filename}")
        
    def print_summary(self):
        """выводим сводку по метрикам"""
        if not self.metrics['memory_usage'] or not self.metrics['cpu_usage']:
            logger.warning("нет данных для анализа")
            return
        
        memory_values = [m['value'] for m in self.metrics['memory_usage']]
        cpu_values = [c['value'] for c in self.metrics['cpu_usage']]
        
        monitoring_time = time.time() - self.start_time if self.start_time else 0
        
        logger.info("сводка по производительности:")
        logger.info(f"   память: среднее {sum(memory_values)/len(memory_values):.1f} МБ, "
                   f"макс {max(memory_values):.1f} МБ, мин {min(memory_values):.1f} МБ")
        logger.info(f"   CPU: среднее {sum(cpu_values)/len(cpu_values):.1f}%, "
                   f"макс {max(cpu_values):.1f}%, мин {min(cpu_values):.1f}%")
        logger.info(f"   время мониторинга: {monitoring_time:.1f} сек")

def main():
    """пример использования монитора"""
    try:
        # можешь передать другой package name если нужно
        monitor = PerformanceMonitor(package_name='ru.proviante')
        
        # начинаем мониторинг
        monitor.start_monitoring()
        
        print("мониторинг запущен. теперь можешь тестировать приложение вручную")
        print("для записи перехода на экран используй: monitor.record_screen_transition('название экрана', время)")
        print("для записи ошибки: monitor.record_error('описание ошибки')")
        print("для остановки нажми Ctrl+C")
        
        # держим мониторинг активным
        while True:
            time.sleep(1)
            
    except RuntimeError as e:
        print(f"ошибка инициализации: {e}")
        print("💡 убедись что:")
        print("   - adb установлен и доступен в PATH")
        print("   - устройство подключено и авторизовано")
        print("   - приложение установлено на устройстве")
    except KeyboardInterrupt:
        print("\nостанавливаем мониторинг...")
        if 'monitor' in locals():
            monitor.stop_monitoring()
            monitor.print_summary()
            monitor.save_metrics()
    except Exception as e:
        print(f"неожиданная ошибка: {e}")
        if 'monitor' in locals():
            monitor.stop_monitoring()

if __name__ == '__main__':
    main() 