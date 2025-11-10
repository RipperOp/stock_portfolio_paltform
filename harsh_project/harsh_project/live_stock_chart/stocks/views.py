from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
import yfinance as yf
import pandas as pd
from .models import PaperAccount, PaperPosition, PaperTransaction
from django.contrib.auth.models import User

# Allowed stock symbols
ALLOWED_STOCKS = [
    "RELIANCE", "TCS", "INFY",  "ICICIBANK",
    "HDFCBANK", "SBIN", "AXISBANK", "LT", "BHARTIARTL",
    "TITAN", "BAJFINANCE", "MARUTI", "SUNPHARMA", "WIPRO",
    "BSE"
]

def strategy(request):
    return render(request, 'strategy.html')

def home(request):
    return render(request, "index.html")

def watchlist(request):
    return render(request, "watchlist.html")

def get_stock_data(request):
    symbol = request.GET.get("symbol")

    if not symbol:
        return JsonResponse({"error": "Stock symbol is required"}, status=400)

    if symbol not in ALLOWED_STOCKS:
        return JsonResponse({"error": "Invalid stock symbol"}, status=400)

    stock_symbol = f"{symbol}.NS"

    try:
        stock = yf.Ticker(stock_symbol)
        hist = stock.history(period="1d", interval="15m")

        if hist.empty:
            return JsonResponse({"error": "No data found for this stock"}, status=404)

        hist = hist.reset_index()
        hist['Datetime'] = hist['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        data = hist[['Datetime', 'Open', 'High', 'Low', 'Close']].to_dict(orient="records")

        return JsonResponse({"symbol": symbol, "data": data})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def portfolio(request):
    try:
        account = PaperAccount.objects.get(user=request.user)
    except PaperAccount.DoesNotExist:
        account = PaperAccount.objects.create(user=request.user)
    
    positions = PaperPosition.objects.filter(account=account)
    
    context = {
        'account': account,
        'positions': positions,
    }
    return render(request, 'paper_trading/portfolio.html', context)

def backtest_stock(request):
    symbol = request.GET.get("symbol")

    if not symbol or symbol not in ALLOWED_STOCKS:
        return JsonResponse({"error": "Invalid or missing stock symbol"}, status=400)

    stock_symbol = f"{symbol}.NS"

    try:
        df = yf.download(tickers=stock_symbol, period="1460d", interval="1d")

        if df.shape[0] == 0:
            return JsonResponse({"error": f"No data found for {symbol}. Try a different stock or period."}, status=404)

        df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()

        trades = []
        position = 0
        entry_price = None
        winning_trades = 0
        losing_trades = 0
        net_profit = 0

        for i in range(1, len(df)):
            close_price = df['Close'].iloc[i]
            ema_21 = df['EMA_21'].iloc[i]
            ema_50 = df['EMA_50'].iloc[i]

            # ✅ Fix: Ensure we use `.iloc[i]` for comparisons
            if float(ema_21) > float(ema_50) and position == 0:
                entry_price = float(close_price)  # Ensure float conversion
                position = 1
                trades.append({
                    "Type": "Buy",
                    "Price": entry_price,
                    "Time": df.index[i].strftime('%Y-%m-%d')
                })

            elif float(ema_21) < float(ema_50) and position == 1:
                exit_price = float(close_price)  # Ensure float conversion
                profit = round(exit_price - entry_price, 2)
                trades.append({
                    "Type": "Sell",
                    "Price": exit_price,
                    "Time": df.index[i].strftime('%Y-%m-%d'),
                    "Profit": profit
                })
                position = 0

                if profit > 0:
                    winning_trades += 1
                else:
                    losing_trades += 1
                net_profit += profit

        return JsonResponse({
            "symbol": symbol,
            "summary": {
                "total_trades": len(trades),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "net_profit": round(net_profit, 2)
            },
            "trades": trades
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def backtest_results(request):
    return render(request, "backtest_results.html")

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'error_message': 'Invalid username or password'})
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# Add login_required decorator to existing views
@login_required(login_url='login')
def home(request):
    try:
        account = PaperAccount.objects.get(user=request.user)
    except PaperAccount.DoesNotExist:
        account = PaperAccount.objects.create(user=request.user)
    
    context = {
        'ALLOWED_STOCKS': ALLOWED_STOCKS,
        'account': account
    }
    return render(request, 'index.html', context)

@login_required(login_url='login')
def strategy(request):
    return render(request, 'strategy.html')

@login_required(login_url='login')
def watchlist(request):
    return render(request, 'watchlist.html')

@login_required(login_url='login')
def backtest_results(request):
    return render(request, 'backtest_results.html')

@login_required(login_url='login')
def paper_trading_dashboard(request):
    try:
        account = PaperAccount.objects.get(user=request.user)
    except PaperAccount.DoesNotExist:
        account = PaperAccount.objects.create(user=request.user)
    
    positions = PaperPosition.objects.filter(account=account)
    transactions = PaperTransaction.objects.filter(account=account).order_by('-created_at')[:10]
    
    context = {
        'account': account,
        'positions': positions,
        'transactions': transactions,
        'ALLOWED_STOCKS': ALLOWED_STOCKS,
    }
    return render(request, 'paper_trading/dashboard.html', context)

@login_required(login_url='login')
def execute_paper_trade(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        action = request.POST.get('action')
        quantity = int(request.POST.get('quantity'))
        
        if not symbol or not action or not quantity:
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        try:
            account = PaperAccount.objects.get(user=request.user)
            stock = yf.Ticker(f"{symbol}.NS")
            current_price = Decimal(str(stock.history(period='1d')['Close'].iloc[-1]))
            total_cost = current_price * quantity
            
            if action == 'BUY':
                if account.balance < total_cost:
                    return JsonResponse({'error': 'Insufficient balance'}, status=400)
                
                # Create transaction
                PaperTransaction.objects.create(
                    account=account,
                    symbol=symbol,
                    transaction_type='BUY',
                    quantity=quantity,
                    price=current_price,
                    total_amount=total_cost
                )
                
                # Update account balance
                account.balance -= total_cost
                account.save()
                
                # Update or create position
                position, created = PaperPosition.objects.get_or_create(
                    account=account,
                    symbol=symbol,
                    defaults={'quantity': quantity, 'average_price': current_price}
                )
                
                if not created:
                    total_shares = position.quantity + quantity
                    new_avg_price = ((position.average_price * position.quantity) + 
                                   (current_price * quantity)) / total_shares
                    position.quantity = total_shares
                    position.average_price = new_avg_price
                    position.save()
                
            elif action == 'SELL':
                try:
                    position = PaperPosition.objects.get(account=account, symbol=symbol)
                    if position.quantity < quantity:
                        return JsonResponse({'error': 'Insufficient shares'}, status=400)
                    
                    # Create transaction
                    PaperTransaction.objects.create(
                        account=account,
                        symbol=symbol,
                        transaction_type='SELL',
                        quantity=quantity,
                        price=current_price,
                        total_amount=total_cost
                    )
                    
                    # Update account balance
                    account.balance += total_cost
                    account.save()
                    
                    # Update position
                    position.quantity -= quantity
                    if position.quantity == 0:
                        position.delete()
                    else:
                        position.save()
                        
                except PaperPosition.DoesNotExist:
                    return JsonResponse({'error': 'No position found for this stock'}, status=400)
            
            return JsonResponse({
                'success': True,
                'message': f'{action} order executed successfully',
                'new_balance': float(account.balance)
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)

@login_required(login_url='login')
def get_portfolio_value(request):
    try:
        account = PaperAccount.objects.get(user=request.user)
        positions = PaperPosition.objects.filter(account=account)
        
        portfolio_value = account.balance
        positions_data = []
        
        for position in positions:
            stock = yf.Ticker(f"{position.symbol}.NS")
            current_price = Decimal(str(stock.history(period='1d')['Close'].iloc[-1]))
            position_value = current_price * position.quantity
            portfolio_value += position_value
            
            positions_data.append({
                'symbol': position.symbol,
                'quantity': position.quantity,
                'average_price': float(position.average_price),
                'current_price': float(current_price),
                'position_value': float(position_value),
                'profit_loss': float(position_value - (position.average_price * position.quantity))
            })
        
        return JsonResponse({
            'total_value': float(portfolio_value),
            'cash_balance': float(account.balance),
            'positions': positions_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if not all([username, email, password1, password2]):
            return render(request, 'register.html', {'error_message': 'All fields are required'})
        
        if password1 != password2:
            return render(request, 'register.html', {'error_message': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error_message': 'Username already exists'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error_message': 'Email already exists'})
        
        try:
            # Create user
            user = User.objects.create_user(username=username, email=email, password=password1)
            
            # Create paper trading account with initial balance
            PaperAccount.objects.create(user=user, balance=100000)
            
            # Log the user in
            login(request, user)
            return redirect('home')
            
        except Exception as e:
            return render(request, 'register.html', {'error_message': str(e)})
    
    return render(request, 'register.html')