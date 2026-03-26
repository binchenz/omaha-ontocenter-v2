#!/usr/bin/env python3
"""Sync Tushare data to local cache."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import tushare as ts
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.cache import CachedStock, CachedFinancialIndicator
from app.config import settings

def sync_stocks(db: Session, pro):
    """Sync stock basic info."""
    print("Syncing stocks...")
    df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')

    for _, row in df.iterrows():
        stock = db.query(CachedStock).filter(CachedStock.ts_code == row['ts_code']).first()
        if not stock:
            stock = CachedStock(ts_code=row['ts_code'])
        stock.symbol = row['symbol']
        stock.name = row['name']
        stock.area = row['area']
        stock.industry = row['industry']
        stock.list_date = row['list_date']
        db.add(stock)

    db.commit()
    print(f"Synced {len(df)} stocks")

def sync_financial_indicators(db: Session, pro):
    """Sync financial indicators."""
    print("Syncing financial indicators...")
    stocks = db.query(CachedStock).all()
    count = 0

    for stock in stocks:
        try:
            df = pro.fina_indicator(ts_code=stock.ts_code, fields='ts_code,end_date,roe,roa,gross_profit_margin,net_profit_margin')
            for _, row in df.iterrows():
                indicator = db.query(CachedFinancialIndicator).filter(
                    CachedFinancialIndicator.ts_code == row['ts_code'],
                    CachedFinancialIndicator.end_date == row['end_date']
                ).first()
                if not indicator:
                    indicator = CachedFinancialIndicator(
                        ts_code=row['ts_code'],
                        end_date=row['end_date'],
                        roe=row['roe'],
                        roa=row['roa'],
                        gross_profit_margin=row['gross_profit_margin'],
                        net_profit_margin=row['net_profit_margin']
                    )
                    db.add(indicator)
            count += len(df)
        except Exception as e:
            print(f"Error syncing {stock.ts_code}: {e}")

    db.commit()
    print(f"Synced {count} financial indicators")

def main():
    token = os.getenv('TUSHARE_TOKEN') or settings.TUSHARE_TOKEN
    if not token:
        print("Error: TUSHARE_TOKEN not set")
        sys.exit(1)

    ts.set_token(token)
    pro = ts.pro_api()
    db = SessionLocal()

    try:
        sync_stocks(db, pro)
        sync_financial_indicators(db, pro)
        print("Sync completed")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == '__main__':
    main()
