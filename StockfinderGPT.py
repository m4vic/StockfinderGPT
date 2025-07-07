import sqlite3
from google import genai
from google.genai import types
import json
import re
from typing import List, Dict, Any, Generator
import time
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor

class NLPStockScreener: # defining the class for Natural Language Stock Screener 
    def __init__(self, api_key: str, db_path: str):
        """
        Initialize the ChatGPT-like Stock Screener
        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"
        self.db_path = db_path
        self.conversation_history = []  # Full conversation context
        self.current_stocks_context = []  # Current stocks being discussed
        
        # System prompt that defines the AI's behavior  and what typr of output we want from it  
        self.system_prompt = """ 
You are an expert financial advisor and stock analyst specializing in Indian markets. 
You have access to a comprehensive database of Indian stocks with fundamental data.

Your personality:
- Friendly, conversational, and approachable
- Expert knowledge but explains things simply
- Asks clarifying questions when needed
- Provides actionable insights
- Mentions specific stock names and data when relevant

Database Schema Available:
- stocks table with: symbol, name, sector, industry, market_cap, pe_ratio, pb_ratio, 
  roe, debt_to_equity, current_ratio, revenue_growth, net_profit_margin, dividend_yield, price, volume

You can help with:
- Stock screening and recommendations
- Fundamental analysis
- Portfolio advice
- Market insights
- Risk assessment

Always provide specific, data-backed reasoning for your recommendations.
"""

    def get_db_connection(self): # connecting the db sql which we have created 
        """Create database connection"""
        return sqlite3.connect(self.db_path)

    async def get_stock_data_async(self, criteria: str) -> List[Dict]: 
        """
        Asynchronously fetch stock data based on criteria
        """
        def fetch_data(): # fetching the data from the db  
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # Smart SQL generation based on criteria
                sql_query = self.generate_smart_sql(criteria)
                cursor.execute(sql_query)
                
                columns = [description[0] for description in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row))) # using zip to save the data one by one in result 
                
                conn.close()
                return results # return result  
            except Exception as e:
                print(f"Database error: {e}")
                return []
        
        # Run database query in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, fetch_data)

    def generate_smart_sql(self, criteria: str) -> str: # sql which is used bt gemeni api to get the required data  
        """
        Generate SQL based on common criteria patterns
        """
        criteria = criteria.lower() # whatever criteria user tells will be lower abd saved in criteria
        
        if any(word in criteria for word in ['value', 'cheap', 'undervalued']): # fg vale,cheap,undervalued will be this sql query used
            return "SELECT * FROM stocks WHERE pe_ratio < 15 AND pb_ratio < 2 AND roe > 10 ORDER BY pe_ratio ASC LIMIT 15"
        
        elif any(word in criteria for word in ['growth', 'growing', 'high growth']):# for growth , growing , high growing this 
            return "SELECT * FROM stocks WHERE revenue_growth > 15 AND roe > 20 ORDER BY revenue_growth DESC LIMIT 15"
        
        elif any(word in criteria for word in ['dividend', 'income', 'yield']): # same
            return "SELECT * FROM stocks WHERE dividend_yield > 2 ORDER BY dividend_yield DESC LIMIT 15"
        
        elif any(word in criteria for word in ['safe', 'stable', 'low risk']): #same
            return "SELECT * FROM stocks WHERE debt_to_equity < 0.5 AND current_ratio > 1.5 AND roe > 10 ORDER BY debt_to_equity ASC LIMIT 15"
        
        elif any(word in criteria for word in ['large cap', 'big', 'large']):#same
            return "SELECT * FROM stocks WHERE market_cap > 50000 ORDER BY market_cap DESC LIMIT 15"
        
        else: # this is default one if any criteria not match still it will find good stocks 
            return "SELECT * FROM stocks WHERE roe > 15 AND pe_ratio < 30 AND debt_to_equity < 1 ORDER BY roe DESC LIMIT 15"

    def create_context_prompt(self, user_message: str, stock_data: List[Dict] = None) -> str: # creating the prompt 
        """
        Create a comprehensive prompt with context
        """
        prompt = f"{self.system_prompt}\n\n" # the prompt which we have declared previously is saved in this prompt var 
        
        # Add conversation history we add the previous conversiation to prompt for better context for api 
        if self.conversation_history:  
            prompt += "Previous conversation:\n"
            for msg in self.conversation_history[-6:]:  # Last 6 messages for context
                prompt += f"User: {msg['user']}\nAssistant: {msg['assistant']}\n\n"
        
        # Add current stock data if available but if it found new stocks related to the prompt it will show case them 
        if stock_data:
            prompt += "Current stock data available:\n"
            for stock in stock_data[:10]:  # Limit to prevent prompt overflow
                prompt += f"• {stock.get('name', 'N/A')} ({stock.get('symbol', 'N/A')}): "
                prompt += f"PE={stock.get('pe_ratio', 'N/A')}, ROE={stock.get('roe', 'N/A')}%, "
                prompt += f"Sector={stock.get('sector', 'N/A')}\n"
            prompt += "\n"
        
        prompt += f"Current user message: {user_message}\n\n" 
        # if user send normal message like hi , hello, etc so reply naturaly
        prompt += "Respond naturally and conversationally. Use the stock data to provide specific recommendations when relevant."
        
        return prompt 

    def stream_response(self, prompt: str) -> Generator[str, None, str]: # adding the live chatgpt like text generation using python time 
        """
        Generate streaming response from LLM
        """
        try:
            # Note: Google's Gemini doesn't support true streaming yet
            # This simulates streaming by chunking the response
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,  # More conversational
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )
            
            full_response = response.text # all the response will be in response variable 
            
            # Simulate streaming with natural pauses 
            sentences = re.split(r'(?<=[.!?])\s+', full_response)
            
            for sentence in sentences:
                words = sentence.split()
                for i, word in enumerate(words):
                    yield word + (" " if i < len(words) - 1 else "")
                    time.sleep(0.05)  # Adjust speed here.  speed of word per nano second 
                
                # Pause at end of sentences
                if sentence.strip().endswith(('.', '!', '?')):
                    yield " "
                    time.sleep(0.2) # the 0.2 second pause at the end of sentences
            
            return full_response # returning full response  
            
        except Exception as e: 
            yield f"I apologize, but I encountered an error: {e}"
            return f"Error: {e}"

    async def process_message_async(self, user_message: str) -> str: # Process user message asynchronously with context awareness . 
        # Determine if we need stock data
        needs_stock_data = any(keyword in user_message.lower() for keyword in [  # the users message will be checked that if it has certain keyword. 
            'find', 'show', 'recommend', 'suggest', 'good', 'best', 'stocks', # keywords to check 
            'companies', 'investment', 'buy', 'portfolio'
        ])
        
        stock_data = [] # declaring a list 
        if needs_stock_data: # if needs stocks data has any keyword than it will be sent to the get_stock_data_async 
            print("🔍 Searching database...", end="", flush=True) 
            stock_data = await self.get_stock_data_async(user_message) # calling the function get stock data with the users message 
            print(f" Found {len(stock_data)} stocks")
            self.current_stocks_context = stock_data # saving the context for future 
        
        # Create context-aware prompt for better cross question 
        prompt = self.create_context_prompt(user_message, stock_data) 
        
        print("\n💡 AI Assistant: ", end="", flush=True)
        
        # Stream the response
        full_response = ""
        for chunk in self.stream_response(prompt): #calling the self.stream_response  with prompt 
            print(chunk, end="", flush=True) # printing the response 
            full_response += chunk # saving the response in full_resopnse
        
        print("\n")
        
        # Store conversation 
        self.conversation_history.append({
            'user': user_message,  # users message in tuple within a dict 
            'assistant': full_response,
            'stocks_context': len(stock_data)
        })
        
        return full_response

    def process_message(self, user_message: str) -> str: #Synchronous wrapper for message processing
        return asyncio.run(self.process_message_async(user_message)) # asyncio.run is used to run async method process_message_async

    def get_conversation_stats(self) -> Dict: # Get conversation statistics 
  
        return { # returns a dict with key to it  
            'total_messages': len(self.conversation_history),
            'stocks_analyzed': len(self.current_stocks_context),
            'last_query_time': time.time()
        }

    def clear_context(self):
        # Clear conversation context for next time 
    
        self.conversation_history = [] 
        self.current_stocks_context = []
        print("✅ Conversation context cleared")

    def show_current_stocks(self):
        """
        Display currently loaded stocks
        """
        if not self.current_stocks_context:
            print("No stocks currently loaded in context")
            return
        
        print(f"\n📊 Current stocks in context ({len(self.current_stocks_context)}):")
        for i, stock in enumerate(self.current_stocks_context[:10], 1):
            print(f"{i}. {stock.get('name', 'N/A')} ({stock.get('symbol', 'N/A')}) - {stock.get('sector', 'N/A')}")
        
        if len(self.current_stocks_context) > 10:
            print(f"... and {len(self.current_stocks_context) - 10} more")

def main():
    """
    Main ChatGPT-like interface
    """
    # Configuration
    API_KEY = "" # enter your API key here make sure it is of gemini which is right now free 
    DB_PATH = "" # the database path which we have saved by running the sql scraper code 
     
    # Initialize screener
    screener = NLPStockScreener(API_KEY, DB_PATH) 
    
    print("🚀 Natural language Stock Screener")
    print("💬 I'm your AI stock advisor. Ask me anything about Indian stocks!")
    print("📋 Commands: /clear (clear context), /stocks (show current stocks), /stats (show stats)")
    print("-" * 60) 
    
    while True:
        try:
            user_input = input("\n🔵 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['/quit', '/exit', 'bye', 'goodbye']:
                print("\n👋 Thanks for using the stock screener! Happy investing!")
                break
            
            elif user_input.lower() == '/clear':
                screener.clear_context()
                continue
            
            elif user_input.lower() == '/stocks':
                screener.show_current_stocks()
                continue
            
            elif user_input.lower() == '/stats':
                stats = screener.get_conversation_stats()
                print(f"📈 Conversation Stats:")
                print(f"  • Messages: {stats['total_messages']}")
                print(f"  • Stocks in context: {stats['stocks_analyzed']}")
                continue
            
            # Process the message
            response = screener.process_message(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Try rephrasing your question or use /clear to reset context")

if __name__ == "__main__":
    main()
