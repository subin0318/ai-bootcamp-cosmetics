# 네이버 쇼핑 검색
import urllib.request
import urllib.parse
import json
import os
from getpass import getpass

# 🔑 API 키: 환경변수에 없으면 실행 시 입력받음 (입력값은 화면에 표시되지 않음)
for name in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "OPENAI_API_KEY"):
    if not os.environ.get(name):
        os.environ[name] = getpass(f"{name} 입력: ").strip()

client_id = os.environ["NAVER_CLIENT_ID"]
client_secret = os.environ["NAVER_CLIENT_SECRET"]

def naver_shop_search(query, max_results=5):
    """
    네이버 쇼핑 검색 API를 사용하여 검색 결과를 하나의 문자열로 반환합니다.

    Parameters:
        query (str): 검색할 키워드
        max_results (int): 검색 결과 중 사용할 최대 개수 (기본값: 5)

    Returns:
        str: 상품명, 요약 정보, 가격 등을 줄바꿈 포함된 문자열로 반환
    """
    enc_query = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/shop.json?query={enc_query}&display={max_results}"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)

    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            response_body = response.read()
            data = json.loads(response_body.decode("utf-8"))
            items = data.get("items", [])

            combined_text = ""
            for idx, item in enumerate(items, start=1):
                title = item.get("title", "").replace("", "").replace("", "")
                lprice = item.get("lprice", "")
                mall_name = item.get("mallName", "")
                combined_text += f"{idx}. {title} (₩{lprice}) - 판매처: {mall_name}\n"

            return combined_text.strip()
        else:
            return f"Error Code: {response.getcode()}"
    except Exception as e:
        return f"Exception occurred: {e}"



# ChatGPT (OPENAI_API_KEY 환경변수 필요)


import gradio as gr
from openai import OpenAI
import json

# OpenAI 클라이언트 초기화
client = OpenAI()

# OpenAI Tool 등록
tools = [
    {
        "type": "function",
        "function": {
            "name": "naver_shop_search",
            "description": "사용자의 입력 프롬프트에 대해서 네이버의 쇼핑 검색을 진행하는 함수입니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "naver_keyword": {
                        "type": "string",
                        "description": "사용자의 입력 프롬프트에서 검색에 필요한 키워드를 추출하여 저장합니다.",
                    },
                },
                "required": ["naver_keyword"]
            },
        },
    },
]

# 응답 생성 함수
def generate_response(prompt_text: str):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "사용자의 입력 프롬프트에 대해서 네이버의 쇼핑 검색을 진행하는 함수를 호출해줘."},
            {"role": "user", "content": prompt_text}
        ],
        tools=tools,
    )

    response = completion.choices[0].message

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        function_name = tool_call.function.name
        arguments_json = json.loads(tool_call.function.arguments)

        if function_name == "naver_shop_search":
            naver_keyword = arguments_json.get('naver_keyword')
            return naver_shop_search(naver_keyword)

        else:
            return "지원되지 않는 함수입니다."


    elif response.function_call:
        return str(response.function_call)

    else:
        return response.content

# Gradio 인터페이스
def chatgpt_interface():
    with gr.Blocks() as demo:
        gr.Markdown("## 💬 ChatGPT에서 네이버 쇼핑 검색 연동하기")

        with gr.Row():
            with gr.Column():
                input_text = gr.Textbox(label="질문을 입력하세요")
                output_text = gr.Textbox(label="AI 응답", interactive=False, lines=10)

                input_text.submit(generate_response, inputs=input_text, outputs=output_text)

        demo.launch()

# 실행
chatgpt_interface()