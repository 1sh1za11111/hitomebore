import streamlit as st
import pandas as pd
import re

# ページ設定
st.set_page_config(page_title="投票集計システム", layout="centered")

st.title("🏆 作品投票・ランキング発表")
st.write("1位(3点)、2位(2点)、3位(1点)を集計します。")

# 1. サイドバーで参加者名簿を設定
st.sidebar.header("⚙️ 設定")
member_input = st.sidebar.text_area(
    "【必須】参加者名簿（1行に1人ずつ）",
    height=300,
    placeholder="石崎 航琉\n奥泉 将章\n...",
    help="ここに名前を入れておくと、0点の人も集計に含まれます。"
)

uploaded_file = st.file_uploader("投票結果CSV（Googleフォームから書き出したもの）をアップロードしてください", type="csv")

if uploaded_file is not None:
    # CSV読み込み
    df = pd.read_csv(uploaded_file)
    
    # 名簿をリスト化
    master_members = [m.strip() for m in member_input.split('\n') if m.strip()]
    
    if not master_members:
        st.warning("👈 左側のサイドバーに参加者名簿を入力してください。")
        st.stop() # 名簿がない場合は一旦停止

    # スコア計算用の辞書を名簿から作成
    stats = {name: {"A": 0, "B": 0, "合計": 0} for name in master_members}

    # 列名の特定（半角/全角の1,2,3位が含まれる列）
    col_1st = [c for c in df.columns if re.search(r'[1１]位', c)]
    col_2nd = [c for c in df.columns if re.search(r'[2２]位', c)]
    col_3rd = [c for c in df.columns if re.search(r'[3３]位', c)]

    if col_1st and col_2nd and col_3rd:
        # 得点集計
        for _, row in df.iterrows():
            for rank_col, points in zip([col_1st[0], col_2nd[0], col_3rd[0]], [3, 2, 1]):
                full_name = str(row[rank_col])
                if pd.isna(row[rank_col]) or full_name == 'nan':
                    continue
                
                parts = full_name.split('_')
                base_name = parts[0].strip()
                suffix = parts[1].upper() if len(parts) > 1 else ""

                # 名簿にない名前が投票された場合の処理
                if base_name not in stats:
                    st.error(f"⚠️ 名簿にない名前への投票があります: {base_name}（{rank_col}）")
                    stats[base_name] = {"A": 0, "B": 0, "合計": 0}

                # 作品別加算
                if suffix == "A":
                    stats[base_name]["A"] += points
                elif suffix == "B":
                    stats[base_name]["B"] += points
                
                stats[base_name]["合計"] += points

        # データフレーム化
        rows = []
        for name, data in stats.items():
            rows.append({
                "制作者名": name,
                "合計得点": data["合計"],
                "作品A": data["A"],
                "作品B": data["B"]
            })
        
        # ソート（得点順 > 名前順）
        full_df = pd.DataFrame(rows).sort_values(by=['合計得点', '制作者名'], ascending=[False, True]).reset_index(drop=True)
        
        # 順位列（1から開始）
        full_df.index = full_df.index + 1
        full_df.index.name = "順位"
        
        # 表示用の装飾
        def decorate_rank(rank):
            if rank == 1: return "🥇 1位"
            if rank == 2: return "🥈 2位"
            if rank == 3: return "🥉 3位"
            return f"{rank}位"

        display_df = full_df.copy().reset_index()
        display_df["順位"] = display_df["順位"].apply(decorate_rank)
        
        # 画面用カラム構成
        display_df = display_df[["順位", "制作者名", "合計得点", "作品A", "作品B"]]

        # 画面表示（上位5名のみ）
        st.subheader("✨ TOP 5 結果発表")
        st.table(display_df.head(5))
        
        # 6位以下の有無をお知らせ
        if len(full_df) > 5:
            st.info(f"💡 6位以下の {len(full_df)-5} 名（0点の人を含む）はダウンロードしたCSVで確認できます。")

        # CSVダウンロード（全データ）
        csv_data = full_df.reset_index().to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="全ての順位結果をCSVで保存",
            data=csv_data,
            file_name='final_ranking_result.csv',
            mime='text/csv',
        )
    else:
        st.error("Googleフォームの列名に '1位', '2位', '3位' が含まれていません。")