"""Run the whole pipeline end to end:  python python/run_all.py"""
import generate_data, clean_data, territory_router, data_quality, generate_insights, build_excel

if __name__ == "__main__":
    for step in (generate_data, clean_data, territory_router, data_quality, generate_insights, build_excel):
        print(f"\n=== {step.__name__} ===")
        step.main()
