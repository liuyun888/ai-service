import httpx

# 演示用公共接口；接真实业务时改成你的 API，并从 config 读 BASE_URL
URL = "https://postman-echo.com/get"


def main() -> None:
    with httpx.Client(timeout=10.0) as client:
        response = client.get(URL)
        print("status:", response.status_code)
        response.raise_for_status()  # 非 2xx 抛异常
        data = response.json()
        print("keys:", list(data.keys()))
        print("sample:", data)


if __name__ == "__main__":
    main()