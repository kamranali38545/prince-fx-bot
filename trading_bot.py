from flask import Flask, jsonify, request
from flask_cors import CORS
import yfinance as yf
import pandas as pd

app = Flask(__name__)
CORS(app)

print("==================================================")
print("   PRINCE.FX.BOT - High-Frequency Signal Engine   ")
print("==================================================")

@app.route('/api/signal', methods=['GET'])
def get_signal():
    ticker = request.args.get('pair', 'USDJPY=X')
    tf = request.args.get('tf', '1m')

    tf_map = {
        '5s': '1m', '15s': '1m', '30s': '1m',
        '1m': '1m', '2m': '2m', '5m': '5m',
        '10m': '15m', '15m': '15m', '30m': '30m'
    }
    fetch_tf = tf_map.get(tf, '1m')

    try:
        data = yf.download(tickers=ticker, period="1d", interval=fetch_tf, progress=False)

        if data.empty:
            return jsonify({"status": "WAIT", "confidence": 50, "price": 0.0, "rsi": 50.0, "trend": "No Data"})

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        data['EMA_5'] = data['Close'].ewm(span=5, adjust=False).mean()
        data['EMA_13'] = data['Close'].ewm(span=13, adjust=False).mean()

        latest_close = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2])
        latest_rsi = float(data['RSI'].iloc[-1])
        ema_5 = float(data['EMA_5'].iloc[-1])
        ema_13 = float(data['EMA_13'].iloc[-1])

        # Active Signal Logic (Reduced WAIT deadzones)
        price_diff = latest_close - prev_close

        if latest_rsi < 48 or (ema_5 > ema_13 and price_diff > 0):
            signal = "BUY"
            confidence = min(98, int(82 + (50 - latest_rsi) * 0.8))
            confidence = max(78, confidence)
            trend = f"Bullish Push ({tf})"
        elif latest_rsi > 52 or (ema_5 < ema_13 and price_diff < 0):
            signal = "SELL"
            confidence = min(98, int(82 + (latest_rsi - 50) * 0.8))
            confidence = max(78, confidence)
            trend = f"Bearish Push ({tf})"
        else:
            signal = "WAIT"
            confidence = 60
            trend = f"Neutral ({tf})"

        return jsonify({
            "status": signal,
            "confidence": confidence,
            "price": round(latest_close, 5),
            "rsi": round(latest_rsi, 2),
            "trend": trend,
            "ticker": ticker
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "WAIT", "confidence": 50, "price": 0.0, "rsi": 0.0, "trend": "Error"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)