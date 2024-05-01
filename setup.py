import yfinance as yf
import pandas as pd
import datetime
#!pip install pytrends
from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError




def download_stock_data(symbol, start_date, end_date):
    try:
        # Daten von Yahoo Finance herunterladen
        data = yf.download(symbol, start=start_date, end=end_date)
        return data
    except Exception as e:
        print("Fehler beim Herunterladen der Daten für", symbol, ":", e)
        return None

def save_to_csv(data, filename):
    try:
        # Daten in eine CSV-Datei speichern
        data.to_csv(filename)
        print("Daten erfolgreich in", filename, "gespeichert.")
    except Exception as e:
        print("Fehler beim Speichern der Daten:", e)

def fill_missing_dates(df):
    copy_df = df.copy()
    desired_index = pd.date_range(start_date, end_date)
    df = copy_df.reindex(desired_index)
    df['Volume'] = df['Volume'].fillna(0)
    df = df.fillna(method='ffill')
    df = df.fillna(0)
    return df

import time

def get_google_trends(keyword, start_date, end_date, geo=''):
    try:
        print(keyword, start_date, end_date, geo)
        pytrends = TrendReq()
        timeframe = start_date.strftime('%Y-%m-%d') + ' ' + end_date.strftime('%Y-%m-%d')
        pytrends.build_payload(kw_list=[keyword], timeframe=timeframe, geo=geo)
        interest_over_time_df = pytrends.interest_over_time()
        print("\nResponse-Code: 200")
        interest_over_time_df.drop(columns=['isPartial'], inplace=True)  # Spalte "isPartial" entfernen
        return interest_over_time_df
    except ResponseError as e:
        if "429" in str(e):  # Überprüfen, ob der Fehlercode 429 ist
            print("\nError: Google returned a response with code 429. Retrying after 1 minute...")
            time.sleep(60)  # 1 Minute warten
            return get_google_trends(keyword, start_date, end_date, geo)  # Anfrage erneut senden
        else:
            print(f"\nError: {e}")
            print(" Filling column with zeros.")
            return pd.DataFrame(index=pd.date_range(start_date, end_date), columns=[keyword]).fillna(0)


def fill_missing_dates_trends(df, start_date, end_date):
    copy_df = df.copy()
    desired_index = pd.date_range(start_date, end_date)
    df = copy_df.reindex(desired_index)
    df = df.fillna(method='ffill')
    df = df.fillna(0)
    return df

def merge_with_google_trends(df, keyword, start_date, end_date, geo, col_name):
    print('Google request: ' + col_name, geo, keyword)
    company_name = company_names.get(keyword)
    if not company_name:
        print(f"Company name not found for keyword '{keyword}'. Filling column with zeros.")
        trends_df = pd.DataFrame(index=pd.date_range(start_date, end_date), columns=[col_name]).fillna(0)
    else:
        try:
            trends_df = get_google_trends(company_name, start_date, end_date, geo)
            trends_df = fill_missing_dates_trends(trends_df, start_date, end_date)
            trends_df.rename(columns={'{}'.format(company_name): col_name}, inplace=True)  # Rename the column
        except KeyError:
            print("Error: 'isPartial' column not found in Google Trends data. Filling column with zeros.")
            trends_df = pd.DataFrame(index=pd.date_range(start_date, end_date), columns=[col_name]).fillna(0)
    df_with_trends = pd.concat([df, trends_df], axis=1)
    return df_with_trends

def combine_indices_data(indices, start_date, end_date):
    indices_data = {}
    for indice in indices:
        data = download_stock_data(indice, start_date, end_date)
        if data is not None:
            data = fill_missing_dates(data)
            indices_data[indice] = data.rename(columns={col: col + '_' + indice for col in data.columns})

    # Combine the indices into a DataFrame
    indices_df = pd.concat(indices_data.values(), axis=1)
    return indices_df




from stock_data import dax_symbols, us_symbols, eu_symbols, company_names, dax_business_fields, us_business_fields, eu_business_fields, indice_symbols, company_country_codes

base_path = "/content/sample_data/stock_data_test2/"

start_date = datetime.datetime(2020, 1, 2)
end_date = datetime.datetime(2020, 2, 5)



symbol_lists = [dax_symbols, us_symbols, eu_symbols]


for symbol_list in symbol_lists:
    for symbol in symbol_list:
        print("#############################################################################################")
        print("#############################################################################################\n")
        
        print("Verarbeite Symbol:", symbol)

        
        data = download_stock_data(symbol, start_date, end_date)
        if data is not None:
            df = pd.DataFrame(data)
            df = df.drop(['Adj Close', 'Open'], axis=1)
            df = fill_missing_dates(df)

            
            if symbol in dax_symbols:
                geo = 'DE'
            elif symbol in us_symbols:
                geo = 'US'
            else:
                geo = company_country_codes[symbol]
            df = merge_with_google_trends(df, symbol, start_date, end_date, geo, 'trends_lokal')
            geo = ''
            df = merge_with_google_trends(df, symbol, start_date, end_date, geo, 'trends_global')

            
            path = base_path + symbol + ".csv"
            save_to_csv(df, path)
        else:
            print("\nFehler beim Herunterladen der Daten für", symbol)

indice_df = combine_indices_data(indice_symbols, start_date, end_date)

if indice_df is not None:
  save_to_csv(indice_df, base_path + 'indices.csv')


all_labels = set(dax_business_fields.values()).union(set(us_business_fields.values()), set(eu_business_fields.values()))

# Sort the labels alphabetically
alphabetical_labels = sorted(all_labels)

# Output the alphabet and its length
print("Alphabet:", alphabetical_labels)
print("Length of Alphabet:", len(alphabetical_labels))

dax_df = pd.DataFrame(list(dax_business_fields.items()), columns=['Symbol', 'Industry'])
dax_df['Region'] = 'DE'

us_df = pd.DataFrame(list(us_business_fields.items()), columns=['Symbol', 'Industry'])
us_df['Region'] = 'US'

eu_df = pd.DataFrame(list(eu_business_fields.items()), columns=['Symbol', 'Industry'])
eu_df['Region'] = 'EU'

# Concatenate all DataFrames
combined_df = pd.concat([dax_df, us_df, eu_df])

for index, row in combined_df.iterrows():
    if row['Region'] == 'EU':
        combined_df.at[index, 'Region'] = company_country_codes[row['Symbol']]
combined_df.reset_index(drop=True, inplace=True)
print("\n")
path = base_path + 'buisness_field_&_origin' + ".csv"
save_to_csv(combined_df, path)
