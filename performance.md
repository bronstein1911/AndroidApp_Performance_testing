- **что делает**:  
  - проверяет подключение `adb` и девайса  
  - каждые 2 сек собирает метрики по имени пакета:  
    - **память** из `dumpsys meminfo` (MB)  
    - **cpu** из `top` по pid (%)  
  - при пиках логирует детали:  
    - **cpu > 20%** — процессы, активные activity  
    - **mem > 200MB** — срезы heap/meminfo  
  - пишет события экранов `record_screen_transition()`, ошибки `record_error()`  
  - по стопу выводит сводку и сохраняет `performance_metrics_YYYYMMDD_HHMMSS.json`

- **как использовать**:  
  - запустить:  
    ```bash
    python performance_test.py
    ```  
  - тестируй аппу, переходы отмечай так в интерактиве:  
    ```python
    monitor.record_screen_transition('экран', 1.23)
    monitor.record_error('описание')
    ```  
  - остановка: `Ctrl+C` → сводка + json  
  - пакет поменять — в `main()` при создании:
    ```python
    PerformanceMonitor(package_name='com.app')
    ```

- **требования**: adb в `PATH`, девайс подключен/авторизован, аппка установлена.