import gradio as gr
import pandas as pd

from main_rule_search import recommend_top5

def run_search(query: str):
    if not query.strip():
        return pd.DataFrame(columns=["rank", "name", "price_krw", "category", "skin_type", "reason"])

    result = recommend_top5(query)
    rows = []

    for i, r in enumerate(result.get("results", []), start=1):
        rows.append({
            "rank": i,
            "name": r.get("name", ""),
            "price_krw": r.get("price_krw", None),
            "category": r.get("category", ""),
            "skin_type": ", ".join(r.get("skin_type", []) or []),
            
        })

    df = pd.DataFrame(rows, columns=["rank", "name", "price_krw", "category", "skin_type"])
    return df

with gr.Blocks(title="화장품 추천 검색 엔진 서비스") as demo:
    gr.Markdown("## 성분 검색 기반 피부 타입 맞춤형 화장품 추천 AI 시스템")
    gr.Markdown("예: 나는 건성 피부야 히알루론산이 들어간 크림 추천해줘")

    query = gr.Textbox(label="검색 문장", lines=2, placeholder="나는 민감성 피부야 코코글루코사이드 들어간 클렌저 추천해줘")
    btn = gr.Button("추천 받기")

    table = gr.Dataframe(
        headers=["rank", "name", "price_krw", "category", "skin_type", "reason"],
        datatype=["number", "str", "number", "str", "str", "str"],
        row_count=5,
        col_count=6,
        interactive=False,
        label="추천 결과 (Top-5)"
    )

    btn.click(run_search, inputs=query, outputs=table)

if __name__ == "__main__":
    demo.launch()
