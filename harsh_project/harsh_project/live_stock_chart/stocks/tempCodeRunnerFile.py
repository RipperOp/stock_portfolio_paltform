def backtest_stock(request):
    symbol = request.GET.get("symbol")

    if not symbol or symbol not in ALLOWED_STOCKS:
        return JsonResponse({"error": "Invalid or missing stock symbol"}, status=400)

    stock_symbol = f"{symbol}.NS"

    try:
        df = yf.download(tickers=stock_symbol, period="180d", interval="1d")

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