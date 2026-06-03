class ChatbotException(Exception):
    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
