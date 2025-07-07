import requests
import sqlite3
import time
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import yfinance as yf

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataScraper:
    def __init__(self, db_path="stocks.db"):
        self.db_path = db_path
        self.setup_database()
        
    def setup_database(self):
        """Create SQLite database and tables for stock fundamentals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create stocks table with key fundamental metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT,
                sector TEXT,
                industry TEXT,
                market_cap REAL,
                pe_ratio REAL,
                pb_ratio REAL,
                roe REAL,
                debt_to_equity REAL,
                current_ratio REAL,
                revenue_growth REAL,
                net_profit_margin REAL,
                dividend_yield REAL,
                price REAL,
                volume INTEGER,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database setup complete")

    def get_nse_top_stocks(self, count=100):
        """Get list of top NSE stocks - expandable list"""
        # NSE Top 100 stocks (you can expand this further)
        nse_stocks = [
            # Top 50 by market cap
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'BHARTIARTL.NS', 'ICICIBANK.NS',
            'INFOSYS.NS', 'LICI.NS', 'SBIN.NS', 'HINDUNILVR.NS', 'ITC.NS',
            'LT.NS', 'HCLTECH.NS', 'BAJFINANCE.NS', 'MARUTI.NS', 'WIPRO.NS',
            'SUNPHARMA.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'BAJAJFINSV.NS',
            'ULTRACEMCO.NS', 'NESTLEIND.NS', 'COALINDIA.NS', 'TITAN.NS', 'AXISBANK.NS',
            'ADANIPOWER.NS', 'KOTAKBANK.NS', 'ASIANPAINT.NS', 'HDFCLIFE.NS', 'TECHM.NS',
            'GRASIM.NS', 'JSWSTEEL.NS', 'INDUSINDBK.NS', 'TATAMOTORS.NS', 'BRITANNIA.NS',
            'CIPLA.NS', 'DRREDDY.NS', 'BPCL.NS', 'EICHERMOT.NS', 'APOLLOHOSP.NS',
            'DIVISLAB.NS', 'TATACONSUM.NS', 'HEROMOTOCO.NS', 'BAJAJ-AUTO.NS', 'HINDALCO.NS',
            'TATASTEEL.NS', 'GODREJCP.NS', 'SHREECEM.NS', 'UPL.NS', 'SBILIFE.NS',
            
            # Next 50 stocks
            'ADANIENT.NS', 'ADANIPORTS.NS', 'AMBUJACEM.NS', 'BANKBARODA.NS', 'BERGEPAINT.NS',
            'BOSCHLTD.NS', 'CANBK.NS', 'CHOLAFIN.NS', 'COLPAL.NS', 'DABUR.NS',
            'DALBHARAT.NS', 'DEEPAKNTR.NS', 'FEDERALBNK.NS', 'GAIL.NS', 'GODREJIND.NS',
            'HAVELLS.NS', 'HDFC.NS', 'HDFCAMC.NS', 'IBULHSGFIN.NS', 'INDIANB.NS',
            'INDIGO.NS', 'INDUSTOWER.NS', 'IOC.NS', 'IRCTC.NS', 'JINDALSTEL.NS',
            'JSWENERGY.NS', 'JUBLFOOD.NS', 'LICHSGFIN.NS', 'M&M.NS', 'MARICO.NS',
            'MOTHERSON.NS', 'MPHASIS.NS', 'MRF.NS', 'MUTHOOTFIN.NS', 'NATIONALUM.NS',
            'NAUKRI.NS', 'NAVINFLUOR.NS', 'NMDC.NS', 'OFSS.NS', 'PAGEIND.NS',
            'PERSISTENT.NS', 'PETRONET.NS', 'PIDILITIND.NS', 'PIIND.NS', 'PNB.NS',
            'POLYCAB.NS', 'PVR.NS', 'RAMCOCEM.NS', 'RECLTD.NS', 'SAIL.NS'
        ]
        return nse_stocks[:count]

    def fetch_stock_data_yfinance(self, symbol):
        """Fetch stock data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Extract key fundamental metrics
            stock_data = {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('forwardPE') or info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'roe': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'revenue_growth': info.get('revenueGrowth'),
                'net_profit_margin': info.get('profitMargins'),
                'dividend_yield': info.get('dividendYield'),
                'price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'volume': info.get('volume')
            }
            
            # Convert percentages to actual percentages
            if stock_data['roe']:
                stock_data['roe'] *= 100
            if stock_data['revenue_growth']:
                stock_data['revenue_growth'] *= 100
            if stock_data['net_profit_margin']:
                stock_data['net_profit_margin'] *= 100
            if stock_data['dividend_yield']:
                stock_data['dividend_yield'] *= 100
                
            return stock_data
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None

    def save_to_database(self, stock_data):
        """Save stock data to SQLite database"""
        if not stock_data:
            return False
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO stocks (
                    symbol, name, sector, industry, market_cap, pe_ratio, pb_ratio,
                    roe, debt_to_equity, current_ratio, revenue_growth, 
                    net_profit_margin, dividend_yield, price, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stock_data['symbol'], stock_data['name'], stock_data['sector'],
                stock_data['industry'], stock_data['market_cap'], stock_data['pe_ratio'],
                stock_data['pb_ratio'], stock_data['roe'], stock_data['debt_to_equity'],
                stock_data['current_ratio'], stock_data['revenue_growth'],
                stock_data['net_profit_margin'], stock_data['dividend_yield'],
                stock_data['price'], stock_data['volume']
            ))
            
            conn.commit()
            logger.info(f"Saved data for {stock_data['symbol']}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving {stock_data['symbol']}: {str(e)}")
            return False
        finally:
            conn.close()

    def scrape_all_stocks(self, batch_size=10, delay=2):
        """Main function to scrape all stocks with better rate limiting"""
        stocks = self.get_nse_top_stocks()
        successful = 0
        failed = 0
        
        logger.info(f"Starting to scrape {len(stocks)} stocks in batches of {batch_size}...")
        
        # Process in batches to avoid rate limits
        for batch_start in range(0, len(stocks), batch_size):
            batch_end = min(batch_start + batch_size, len(stocks))
            batch = stocks[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}: stocks {batch_start+1}-{batch_end}")
            
            for i, symbol in enumerate(batch):
                logger.info(f"Processing {symbol} ({batch_start + i + 1}/{len(stocks)})")
                
                # Retry mechanism for failed requests
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        stock_data = self.fetch_stock_data_yfinance(symbol)
                        
                        if stock_data and self.save_to_database(stock_data):
                            successful += 1
                            break
                        else:
                            if attempt == max_retries - 1:
                                failed += 1
                                logger.warning(f"Failed to process {symbol} after {max_retries} attempts")
                    
                    except Exception as e:
                        logger.error(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(delay * 2)  # Longer delay on retry
                        else:
                            failed += 1
                
                # Rate limiting - wait between requests
                time.sleep(delay)
            
            # Longer break between batches
            if batch_end < len(stocks):
                logger.info(f"Batch complete. Waiting {delay * 3} seconds before next batch...")
                time.sleep(delay * 3)
        
        logger.info(f"Scraping complete! Success: {successful}, Failed: {failed}")
        return successful, failed

    def get_stock_summary(self):
        """Get summary of scraped data"""
        conn = sqlite3.connect(self.db_path)
        
        # Get basic stats
        total_stocks = pd.read_sql_query("SELECT COUNT(*) as count FROM stocks", conn)
        sectors = pd.read_sql_query("SELECT sector, COUNT(*) as count FROM stocks WHERE sector IS NOT NULL GROUP BY sector", conn)
        
        print(f"\n📊 Database Summary:")
        print(f"Total stocks: {total_stocks.iloc[0]['count']}")
        print(f"\nSector distribution:")
        print(sectors.to_string(index=False))
        
        # Sample data
        sample = pd.read_sql_query("""
            SELECT symbol, name, sector, pe_ratio, roe, debt_to_equity 
            FROM stocks 
            WHERE pe_ratio IS NOT NULL 
            LIMIT 5
        """, conn)
        
        print(f"\nSample data:")
        print(sample.to_string(index=False))
        
        conn.close()

# Usage example
if __name__ == "__main__":
    scraper = StockDataScraper()
    
    # Scrape all stocks
    success, failed = scraper.scrape_all_stocks()
    
    # Show summary
    scraper.get_stock_summary()
    
    print(f"\n✅ Scraping completed: {success} successful, {failed} failed")
