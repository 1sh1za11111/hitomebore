import streamlit as st
import pandas as pd
import re

# ページ設定
st.set_page_config(page_title="感想付き・投票集計システム", layout="wide")

st.title("🏆 感想付き・ランキング集計ツール")
st.write("得点集計と同時に、各作品への「理由・感想」を整理します。")

# 1. ファイルアップローダー
vote_file = st.file_uploader("1. 投票結果CSV（Googleフォーム）", type="csv")
mapping_file = st.file_uploader("2. 【任意】ID対応表CSV", type="csv")

def normalize_id(val):
    if pd.isna(val): return None
    return str(val).strip().lstrip('0')

if vote_file is not None:
    vote_df = pd.read_csv(vote_file)
    
    # 2. ID対応表の処理
    mapping_dict = {} # ID -> 名前
    id_to_type = {}   # ID -> "A" or "B"
    name_to_ids = {}  # 名前 -> {"A": id1, "B": id2}
    use_mapping = False

    if mapping_file is not None:
        mapping_df = pd.read_csv(mapping_file)
        for _, row in mapping_df.iterrows():
            name = str(row['名前']).strip()
            id1 = normalize_id(row['ID1'])
            id2 = normalize_id(row['ID2'])
            mapping_dict[id1], id_to_type[id1] = name, "A"
            mapping_dict[id2], id_to_type[id2] = name, "B"
            name_to_ids[name] = {"A": id1, "B": id2}
        use_mapping = True
    else:
        st.warning("⚠️ ID対応表がアップロードされていません。")
        ans = st.radio("このままIDのみで集計しますか？", ("選択してください", "はい", "いいえ"))
        if ans != "はい": st.stop()
        use_mapping = False

    # 3. 集計 & 感想抽出
    rank_cols = [c for c in vote_df.columns if re.search(r'[1-3１-３]位', c)]
    stats = {} 

    for _, row in vote_df.iterrows():
        for col in rank_cols:
            raw_id = normalize_id(row[col])
            if not raw_id: continue
            
            # 得点判定
            points = 3 if '1' in col or '１' in col else (2 if '2' in col or '２' in col else 1)
            
            # 感想の取得（ID列の右隣）
            col_idx = vote_df.columns.get_loc(col)
            reason = str(row.iloc[col_idx + 1]).strip() if col_idx + 1 < len(vote_df.columns) else ""
            if reason == "nan" or not reason: reason = ""

            key = mapping_dict.get(raw_id, raw_id) if use_mapping else raw_id
            
            if key not in stats:
                stats[key] = {"合計": 0, "A_score": 0, "B_score": 0, "A_reasons": [], "B_reasons": [], "ID_reasons": []}
            
            stats[key]["合計"] += points
            
            if use_mapping:
                work_type = id_to_type.get(raw_id, "不明")
                if work_type == "A":
                    stats[key]["A_score"] += points
                    if reason: stats[key]["A_reasons"].append(reason)
                elif work_type == "B":
                    stats[key]["B_score"] += points
                    if reason: stats[key]["B_reasons"].append(reason)
            else:
                if reason: stats[key]["ID_reasons"].append(reason)

    # 4. データ整形
    result_rows = []
    for key, data in stats.items():
        row_data = {"合計得点": data["合計"]}
        if use_mapping:
            row_data["制作者名"] = key
            row_data["作品A得点"] = data["A_score"]
            row_data["作品B得点"] = data["B_score"]
            
            # 感想の整形：冒頭に一度だけ見出しを付ける
            ids = name_to_ids.get(key, {"A": "?", "B": "?"})
            row_data["作品Aへの感想"] = f"【{ids['A']}】への感想 : " + " / ".join(data["A_reasons"]) if data["A_reasons"] else ""
            row_data["作品Bへの感想"] = f"【{ids['B']}】への感想 : " + " / ".join(data["B_reasons"]) if data["B_reasons"] else ""
        else:
            row_data["ID"] = key
            row_data["このIDへの感想"] = f"【{key}】への感想 : " + " / ".join(data["ID_reasons"]) if data["ID_reasons"] else ""
        result_rows.append(row_data)

    res_df = pd.DataFrame(result_rows)
    res_df['順位'] = res_df['合計得点'].rank(method='min', ascending=False).astype(int)
    sort_col = "制作者名" if use_mapping else "ID"
    res_df = res_df.sort_values(by=['順位', sort_col]).reset_index(drop=True)

    # 5. 表示
    def decorate_rank(rank):
        if rank == 1: return "🥇 1位"
        if rank == 2: return "🥈 2位"
        if rank == 3: return "🥉 3位"
        return f"{rank}位"

    display_df = res_df.copy()
    display_df["順位表示"] = display_df["順位"].apply(decorate_rank)
    st.subheader("✨ TOP 5 結果発表")
    show_cols = ["順位表示", sort_col, "合計得点"] + (["作品A得点", "作品B得点"] if use_mapping else [])
    st.table(display_df[res_df['順位'] <= 5][show_cols])

    # 6. ダウンロード
    csv = res_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(label="感想付き全結果をCSVで保存", data=csv, file_name='ranking_result.csv', mime='text/csv')