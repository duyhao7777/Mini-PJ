from adventureworks_bi.utils.etl_helpers import get_connection

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def save_ai_summaries(df, *args, **kwargs):
    if df.empty:
        print('Không có lời giải thích mới để lưu.')
        return
    with get_connection() as loader:
        for r in df.to_dict('records'):
            text = str(r['summary_text']).replace("'", "''")
            model = str(r['model_name']).replace("'", "''")
            loader.execute(
                f"INSERT INTO etl.run_ai_summary (run_id, summary_text, model_name) "
                f"VALUES ({int(r['run_id'])}, N'{text}', '{model}')"
            )
        loader.commit()
    print(f'Đã lưu {len(df)} lời giải thích vào etl.run_ai_summary')