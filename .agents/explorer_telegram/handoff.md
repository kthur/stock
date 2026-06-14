# Handoff Report: Telegram Integration & Fallback Design

## 1. Observation
We examined the following files:
* **`trading_system/telegram_bot_runner.py`**:
  * Line 31-34:
    ```python
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        return
    ```
  * Line 62:
    ```python
    await application.bot.send_message(chat_id=user_id, text=msg)
    ```
  * Line 66:
    ```python
    system.event_bus.subscribe("order_status", on_order_status_event)
    ```
* **`trading_system/src/telegram_bot/bot_engine.py`**:
  * Line 29:
    ```python
    self.api_token = api_token or os.getenv("TELEGRAM_BOT_TOKEN")
    ```
  * Line 78-80:
    ```python
    if not self.api_token:
        self.logger.warning("TELEGRAM_BOT_TOKEN not set. Using simulation mode.")
        self.simulation_mode = True
    ```
* **`trading_system/src/utils/notifier.py`**:
  * Line 17-20:
    ```python
    async def send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            return
    ```
* **`trading_system/trading_system.py`**:
  * Line 1579-1581:
    ```python
    def send_telegram_notification(self, user_id: int, event_type: str, data: Dict) -> str:
        """텔레그램 알림 전송"""
        return self.telegram_bot.get_notification(event_type, data)
    ```

---

## 2. Logic Chain
1. **Programmatic Notification Alerts**:
   * According to `telegram_bot_runner.py` (line 66) and `trading_system/trading_system.py` (line 1579), the live runner subscribes to event bus topic `"order_status"`.
   * When `OrderManagement` publishes `"order_status"`, the runner invokes `on_order_status_event`, formatting the message text via the system's `send_telegram_notification` (which uses `TelegramBotEngine.get_notification` to format the message).
   * It then makes an asynchronous network call `await application.bot.send_message(chat_id=user_id, text=msg)`.
2. **Fallback Behaviors**:
   * Currently, the live daemon `telegram_bot_runner.py` immediately logs an error and exits if `TELEGRAM_BOT_TOKEN` is missing (line 31-34).
   * The `NotificationSystem` in `notifier.py` silently exits if `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` are missing (line 17-20).
3. **Resilient Design Proposal**:
   * To prevent crashes and silence, a simulation mode should be triggered when settings are missing. This simulation mode will intercept outbound API requests, log them as warnings, and print them to standard output/file logging, rather than calling the API or exiting.

---

## 3. Caveats
* We did not run the live Telegram runner daemon because a live token is required, and network calls are restricted in `CODE_ONLY` mode.
* The `NotificationSystem` (`src/utils/notifier.py`) is fully declared but currently not referenced or used by any other class in the repository.

---

## 4. Conclusion
Programmatic alert notifications are triggered via the EventBus and formatted by `TelegramBotEngine`, but they rely on `telegram_bot_runner.py`'s active python-telegram-bot connection. Adding a resilient fallback in the runner and one-way notifier classes ensures that local executions and pipeline scheduler daemons log alerts to stdout and the local file system without causing application crashes.

---

## 5. Verification Method
1. **Run existing test suite**:
   Execute the pytest test command to ensure the current mock Telegram tests continue to pass:
   ```bash
   pytest trading_system/tests/test_telegram_bot.py
   ```
2. **Simulated Fallback Verification**:
   Verify that without a token set:
   * Running `python trading_system/demo_telegram.py` runs successfully in simulation mode without calling any external HTTP endpoints.
   * Modifying configuration to skip token causes warnings to be generated in the application's stderr log and print formatting to console.
