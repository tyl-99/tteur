import pandas as pd

def get_top_parameters(filename="autotuner_results_20250911_131617.xlsx", num_results=10):
    try:
        df = pd.read_excel(filename)
        df_sorted = df.sort_values(by='win_rate', ascending=False)
        
        print(f"\n--- Top {num_results} Parameter Combinations by Win Rate ---")
        for i, row in df_sorted.head(num_results).iterrows():
            print(f"\nCombination ID: {int(row['combination_id'])}")
            print(f"Win Rate: {row['win_rate']:.2f}%")
            print(f"Total PnL: {row['total_pnl']:.2f}")
            print("Parameters:")
            # Exclude metrics and combination_id from parameters
            params = {k: v for k, v in row.items() if k not in ['combination_id', 'total_trades', 'win_rate', 'total_pnl', 'final_balance', 'max_drawdown', 'sharpe_ratio']}
            for param, value in params.items():
                print(f"  {param}: {value}")
            
    except FileNotFoundError:
        print(f"Error: File {filename} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_top_parameters()
