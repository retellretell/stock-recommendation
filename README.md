# 📈 Stock Weather Dashboard

AI-powered stock market weather forecast - An intuitive web service showing rise/fall probabilities

![Stock Weather Dashboard](./docs/screenshot.png)

## 🌟 Key Features

- **🌤️ Weather Metaphor**: Intuitive representation of complex stock markets as weather forecasts
- **📊 AI Predictions**: Rise/fall probability predictions using LSTM, GRU, XGBoost ensemble models
- **💎 Fundamental Analysis**: Scoring based on ROE, EPS, and revenue growth rates
- **🎯 Sector Weather Map**: Market temperature by industry at a glance
- **💰 Completely Free**: All features available at no cost

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 14+
- Git

### Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

python main.py

