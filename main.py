# Ganesha

def main():
    from breeze_connect import BreezeConnect
    import pandas as pd
    import login as l
    from dateutil.relativedelta import relativedelta, TH
    from  datetime import datetime, date, time, timedelta
    import time as ti
    import warnings
    warnings.filterwarnings("ignore")



    breeze = BreezeConnect(api_key=l.api_key)
    breeze.generate_session(api_secret=l.api_secret, session_token =l.session_key)
    d = datetime.utcnow()
    # current_expiry_dt = l.current_expiry_dt


    NSE_master = pd.read_csv('NSEScripMaster.csv')
    NSE_master.columns = [i[2:-1] for i in NSE_master.columns]
    nifty100 = pd.read_csv('ind_nifty100list.csv')
    nifty100.rename(columns={'ISIN Code': 'ISINCode'}, inplace=True)
    sorted_codes = nifty100.merge(NSE_master, how='left', on='ISINCode')[['ShortName','CompanyName']]
    sorted_codes.loc[~sorted_codes['ShortName'].isin(['ZOMLIM', 'ONE97'])]
    sorted_codes.columns = ['code', 'company_name']


    today = date.today()
    yesterday = today - timedelta(days = 1)

    if yesterday.weekday() ==6:
        yesterday=yesterday-timedelta(days=2)
        

    if yesterday.weekday() ==5:
        yesterday=yesterday-timedelta(days=1)
        
    for i in range(1,len(sorted_codes)):
        try:
            print("*******************************************************************************************************")
            code = str(sorted_codes.loc[i, "code"])
            stock_type = 'Cash' 
            print("for stock :", code)

            Stock_strike = breeze.get_historical_data(interval="1day",
                                        from_date= str(yesterday),
                                        to_date= str(yesterday),
                                        stock_code=code,
                                        exchange_code="NSE",
                                        product_type=stock_type,
                                        right="others",
                                        strike_price="0")

            df_stock = pd.DataFrame(Stock_strike['Success'])

            prev_day_stock_low = pd.to_numeric(df_stock['low'].iloc[0])
            prev_day_stock_low = float(prev_day_stock_low)  
            print("Prev Day Low :", prev_day_stock_low)

            today_stock = breeze.get_historical_data(interval="5minute",
                                        from_date= str(datetime.now()),
                                        to_date= str(datetime.now()),
                                        stock_code=code,
                                        exchange_code="NSE",
                                        product_type=stock_type,
                                        expiry_date=str(datetime.now()),
                                        right="others",
                                        strike_price="0")

                
            
            df_stock = pd.DataFrame(today_stock['Success'])
            df_new = df_stock[(pd.to_datetime(df_stock['datetime']).dt.time <= time(14,55)) & (pd.to_datetime(df_stock['datetime']).dt.time >= time(9,15))]
            
            df_new['datetime']= pd.to_datetime(df_new['datetime'])

            current_candle = df_new.iloc[-2]
            prev_candle = df_new.iloc[-3]
            
            print("Previous_candle Low :", prev_candle['low'])
            print("current_candle Close :", current_candle['close'])
            
            flag = 0
            target = float('inf')
            if flag == 0 and pd.to_numeric(current_candle['close']) <= prev_day_stock_low:
                flag = 1
            flag

            if flag == 1 and pd.to_numeric(current_candle['close']) >= prev_day_stock_low:
                flag = 2
                diff = abs(pd.to_numeric(current_candle['close']) - pd.to_numeric(prev_candle['low']))
            

            if flag == 2 and pd.to_numeric(current_candle['close']) >= float(target):
                buy_cash = breeze.place_order(stock_code=code,
                            exchange_code="NSE",
                            product=stock_type,
                            action="buy",
                            order_type="market",
                            stoploss="",
                            quantity="1",
                            validity="day")

                orderid = buy_cash['Success']['order_id']
                print(orderid)

                stop_loss = float(list(breeze.get_trade_detail(exchange_code=stock_type,order_id=orderid)['Success'])[0]['execution_price'])- diff
                target = pd.to_numeric(current_candle['close']) + 1.5 * diff 
                print("*******************************************************************************************************")
                check_time = datetime.utcnow().time()

        

            if check_time > time(14,55):

                today_date = datetime.today().replace(minute=0, hour=0, second=0, microsecond=0).isoformat()[:19]+ '.000Z'
                order_list = pd.DataFrame(breeze.get_order_list(exchange_code=stock_type,
                                    from_date=today_date,
                                    to_date=today_date)['Success'])

                portfolio = breeze.get_portfolio_positions()['Success']
                i = 0

                while portfolio != None and i < len(portfolio):
                    breeze.square_off(exchange_code=stock_type,
                                product=stock_type,
                                stock_code=portfolio[i]['stock_code'],
                                # expiry_date=portfolio[i]['expiry_date'],
                                # right=portfolio[i]['right'],
                                # strike_price=portfolio[i]['strike_price'],
                                action="sell",
                                order_type="market",
                                validity="day",
                                # stoploss=stop_loss,
                                quantity="1",
                                price=stop_loss,
                                # trade_password="",
                                disclosed_quantity="0")
                    portfolio = breeze.get_portfolio_positions()['Success']
                    i+=1

                #cancell all pending orders
                [breeze.cancel_order(exchange_code=stock_type,order_id=i) for i in list(order_list[order_list['order_type']=='StopLoss']['order_id'])]
        except:
            pass
    return None