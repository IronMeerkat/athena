import yfinance as yf
from langchain_anthropic import ChatAnthropic
from athena_settings import settings
from langchain_anthropic import convert_to_anthropic_tool
from langchain_core.tools import tool as core_tool
from langchain_core.tools import Tool
from typing import List
from athena_logging import get_logger

logger = get_logger(__name__)

llm = ChatAnthropic(model="claude-sonnet-4-20250514", anthropic_api_key=settings.ANTHROPIC_API_KEY, temperature=0.1)

finance_tools: List[Tool] = []

def anthropic_tool(func):
    tool = convert_to_anthropic_tool(core_tool(func))
    finance_tools.append(tool)
    return tool

@anthropic_tool
def get_stock_price(ticker: str) -> float:
    """Get the current price of a stock"""
    stock = yf.Ticker(ticker)
    return stock.info['regularMarketPrice']

@anthropic_tool
def get_stock_info(ticker: str) -> dict:
    """Get comprehensive stock information including price, market cap, ratios, and company details"""
    stock = yf.Ticker(ticker)
    return stock.info

@anthropic_tool
def get_stock_income_stmt(ticker: str) -> dict:
    """Get annual income statement showing revenue, expenses, and profit/loss"""
    stock = yf.Ticker(ticker)
    return stock.income_stmt

@anthropic_tool
def get_stock_balance_sheet(ticker: str) -> dict:
    """Get the annual balance sheet showing company's assets, liabilities, and equity"""
    stock = yf.Ticker(ticker)
    return stock.balance_sheet

@anthropic_tool
def get_stock_cashflow(ticker: str) -> dict:
    """Get annual cash flow statement showing operating, investing, and financing cash flows"""
    stock = yf.Ticker(ticker)
    return stock.cashflow

@anthropic_tool
def get_stock_quarterly_income_stmt(ticker: str) -> dict:
    """Get quarterly income statements for more recent financial performance"""
    stock = yf.Ticker(ticker)
    return stock.quarterly_income_stmt

@anthropic_tool
def get_stock_quarterly_cashflow(ticker: str) -> dict:
    """Get quarterly cash flow statements for recent cash generation analysis"""
    stock = yf.Ticker(ticker)
    return stock.quarterly_cashflow

@anthropic_tool
def get_stock_ttm_income_stmt(ticker: str) -> dict:
    """Get trailing twelve months income statement for current year performance"""
    stock = yf.Ticker(ticker)
    return stock.ttm_income_stmt

@anthropic_tool
def get_stock_ttm_cashflow(ticker: str) -> dict:
    """Get trailing twelve months cash flow for current year cash generation"""
    stock = yf.Ticker(ticker)
    return stock.ttm_cashflow

@anthropic_tool
def get_stock_earnings(ticker: str) -> dict:
    """Get earnings data including EPS history and estimates"""
    stock = yf.Ticker(ticker)
    return stock.earnings

@anthropic_tool
def get_stock_calendar(ticker: str) -> dict:
    """Get upcoming earnings dates, dividend dates, and other important events"""
    stock = yf.Ticker(ticker)
    return stock.calendar

@anthropic_tool
def get_stock_earnings_dates(ticker: str) -> dict:
    """Get historical and upcoming earnings announcement dates with estimates"""
    stock = yf.Ticker(ticker)
    return stock.earnings_dates

@anthropic_tool
def get_stock_sec_filings(ticker: str) -> dict:
    """Get recent SEC filings (10-K, 10-Q, 8-K) for regulatory disclosures"""
    stock = yf.Ticker(ticker)
    return stock.sec_filings

@anthropic_tool
def get_stock_history(ticker: str, period: str = "1y") -> dict:
    """Get historical price data (open, high, low, close, volume) for specified period"""
    stock = yf.Ticker(ticker)
    return stock.history(period=period)

@anthropic_tool
def get_stock_dividends(ticker: str) -> dict:
    """Get historical dividend payments and dates"""
    stock = yf.Ticker(ticker)
    return stock.dividends

@anthropic_tool
def get_stock_splits(ticker: str) -> dict:
    """Get historical stock split dates and ratios"""
    stock = yf.Ticker(ticker)
    return stock.splits

@anthropic_tool
def get_stock_news(ticker: str, count: int = 10) -> list:
    """Get latest news articles related to the stock"""
    stock = yf.Ticker(ticker)
    return stock.get_news(count=count)

@anthropic_tool
def get_stock_fast_info(ticker: str) -> dict:
    """Get quick access to key metrics like market cap, price, shares outstanding"""
    stock = yf.Ticker(ticker)
    return stock.fast_info

@anthropic_tool
def get_stock_recommendations(ticker: str) -> dict:
    """Get analyst recommendations breakdown (strong buy, buy, hold, sell, strong sell)"""
    stock = yf.Ticker(ticker)
    return stock.recommendations

@anthropic_tool
def get_stock_recommendations_summary(ticker: str) -> dict:
    """Get summary of analyst recommendation changes over time"""
    stock = yf.Ticker(ticker)
    return stock.recommendations_summary

@anthropic_tool
def get_stock_upgrades_downgrades(ticker: str) -> dict:
    """Get recent analyst upgrades and downgrades with firm names and reasons"""
    stock = yf.Ticker(ticker)
    return stock.upgrades_downgrades

@anthropic_tool
def get_stock_analyst_price_targets(ticker: str) -> dict:
    """Get analyst price targets including high, low, mean, and median estimates"""
    stock = yf.Ticker(ticker)
    return stock.analyst_price_targets

@anthropic_tool
def get_stock_earnings_estimate(ticker: str) -> dict:
    """Get forward earnings estimates from analysts"""
    stock = yf.Ticker(ticker)
    return stock.earnings_estimate

@anthropic_tool
def get_stock_revenue_estimate(ticker: str) -> dict:
    """Get forward revenue estimates from analysts"""
    stock = yf.Ticker(ticker)
    return stock.revenue_estimate

@anthropic_tool
def get_stock_earnings_history(ticker: str) -> dict:
    """Get historical earnings vs estimates (actual vs expected EPS)"""
    stock = yf.Ticker(ticker)
    return stock.earnings_history

@anthropic_tool
def get_stock_eps_trend(ticker: str) -> dict:
    """Get EPS estimate trends showing how estimates have changed over time"""
    stock = yf.Ticker(ticker)
    return stock.eps_trend

@anthropic_tool
def get_stock_eps_revisions(ticker: str) -> dict:
    """Get recent EPS estimate revisions (up/down revisions by analysts)"""
    stock = yf.Ticker(ticker)
    return stock.eps_revisions

@anthropic_tool
def get_stock_growth_estimates(ticker: str) -> dict:
    """Get growth rate estimates for stock vs industry, sector, and market"""
    stock = yf.Ticker(ticker)
    return stock.growth_estimates

@anthropic_tool
def get_stock_major_holders(ticker: str) -> dict:
    """Get major shareholders and ownership percentages"""
    stock = yf.Ticker(ticker)
    return stock.major_holders

@anthropic_tool
def get_stock_institutional_holders(ticker: str) -> dict:
    """Get institutional ownership details (funds, pensions, etc.)"""
    stock = yf.Ticker(ticker)
    return stock.institutional_holders

@anthropic_tool
def get_stock_mutualfund_holders(ticker: str) -> dict:
    """Get mutual fund ownership details and holdings"""
    stock = yf.Ticker(ticker)
    return stock.mutualfund_holders

@anthropic_tool
def get_stock_insider_purchases(ticker: str) -> dict:
    """Get recent insider buying activity (executives, directors purchasing stock)"""
    stock = yf.Ticker(ticker)
    return stock.insider_purchases

@anthropic_tool
def get_stock_insider_transactions(ticker: str) -> dict:
    """Get all insider transactions including buys, sells, and option exercises"""
    stock = yf.Ticker(ticker)
    return stock.insider_transactions

@anthropic_tool
def search_stocks(query: str, max_results: int = 10) -> list:
    """Search for stocks by company name or ticker and get matching quotes"""
    search = yf.Search(query, max_results=max_results)
    return search.quotes

@anthropic_tool
def search_stock_news(query: str, news_count: int = 10) -> list:
    """Search for news articles related to a company or stock query"""
    search = yf.Search(query, news_count=news_count)
    return search.news

@anthropic_tool
def search_stock_research(query: str, max_results: int = 10) -> list:
    """Search for research reports and analysis related to a company or stock"""
    search = yf.Search(query, max_results=max_results, include_research=True)
    return search.research

llm_with_finance_tools = llm.bind(tools=finance_tools)

def call_finance_agent(query: str) -> str:
    """Call the finance agent to get the answer to the question"""
    return_me = llm_with_finance_tools.invoke(query)
    logger.info(f"Return message: {return_me}")
    return return_me.content