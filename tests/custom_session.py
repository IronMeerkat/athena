from requests.sessions import Session
from requests import Response
import json

class CustomResponse(Response):

    def __init__(self, response) -> None:
        self.__dict__ = {**response.__dict__}

    def __repr__(self) -> str:
        try:
            return json.dumps(self.json())
        except:
            return str(self.content)

    def __getitem__(self, key):
        return self.json()[key]

class CustomSession(Session):

    def __init__(self, baseurl: str, login_endpoint: str, **login_credentials):

        super().__init__()
        self.cache_disabled = True
        self.baseurl = baseurl

        auth = self.post(login_endpoint, json=login_credentials)
        self.headers.update({'Authorization': f"Bearer {auth['access']}"})
        self.cookies.set('refresh', auth['refresh'])


    def request(self, method, url, **kwargs) -> CustomResponse:
        url = f"{self.baseurl}{url}"
        resp = super().request(method, url, **kwargs)
        return CustomResponse(resp)


custom_session = CustomSession(baseurl="http://localhost:8000", login_endpoint="/api/token/", username="athena", password="athena")