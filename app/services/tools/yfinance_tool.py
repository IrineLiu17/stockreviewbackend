"""
YFinance Tool - Fetches real-time market data
"""
import yfinance as yf
from typing import Optional, Dict, Any
import re

class YFinanceTool:
    """Tool for fetching market data via YFinance"""
    
    def __init__(self):
        pass
    
    def extract_stock_symbols(self, text: str) -> list[str]:
        """Extract potential stock symbols from text"""
        # Look for common patterns: $AAPL, AAPL, 苹果股票, etc.
        symbols = []
        
        # Pattern for $SYMBOL
        dollar_pattern = r'\$([A-Z]{1,5})'
        symbols.extend(re.findall(dollar_pattern, text.upper()))
        
        # Pattern for standalone symbols (2-5 uppercase letters)
        standalone_pattern = r'\b([A-Z]{2,5})\b'
        potential = re.findall(standalone_pattern, text.upper())
        # Filter out common words
        common_words = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY', 'WHO', 'BOY', 'DID', 'ITS', 'LET', 'PUT', 'SAY', 'SHE', 'TOO', 'USE'}
        symbols.extend([s for s in potential if s not in common_words])
        
        return list(set(symbols[:5]))  # Limit to 5 symbols
    
    async def get_market_context(
        self,
        note
    ) -> Dict[str, Any]:
        """Get market context for a note"""
        # Extract stock symbols from note text
        text = f"{note.question1} {note.question2} {note.question3}"
        symbols = self.extract_stock_symbols(text)
        
        if not symbols:
            return {}
        
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Get current price
                hist = ticker.history(period="1d")
                current_price = float(hist['Close'].iloc[-1]) if not hist.empty else None
                
                market_data[symbol] = {
                    "name": info.get("longName", symbol),
                    "current_price": current_price,
                    "previous_close": info.get("previousClose"),
                    "change_percent": info.get("regularMarketChangePercent"),
                    "market_cap": info.get("marketCap"),
                }
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                continue
        
        return market_data
