import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from datetime import datetime

def fetch_temperature(city, api_key ):
    params = {'q': city, 'appid': api_key, 'units': 'metric'}
    response = requests.get('http://api.openweathermap.org/data/2.5/weather', params=params)
    return response

def detect_temperature_anomaly(data, city, current_temp):
    current_month = datetime.now().month
    monthly_data = data[(data['city'] == city) & (data['timestamp'].dt.month == current_month)]

    if monthly_data.empty:
        return False, None, None

    mean_temp = monthly_data['temperature'].mean()
    std_temp = monthly_data['temperature'].std()
    is_anomaly = abs(current_temp - mean_temp) >= 2 * std_temp

    return is_anomaly, mean_temp, std_temp

def analyze_data(data):
    data['rolling_avg'] = data.groupby('city')['temperature'].rolling(window=30).mean().reset_index(0, drop=True)
    data['rolling_std'] = data.groupby('city')['temperature'].rolling(window=30).std().reset_index(0, drop=True)
    data['rolling_avg'] = data['rolling_avg'].fillna(method='bfill')
    data['rolling_std'] = data['rolling_std'].fillna(method='bfill')
    data['anomaly'] = abs(data['temperature'] - data['rolling_avg']) >= 2 * data['rolling_std']
    return data

def plot_horizontal_temperature_range(mean_temp, std_temp, current_temp):
    lower_bound, upper_bound = mean_temp - 2 * std_temp, mean_temp + 2 * std_temp
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=[mean_temp, mean_temp], y=[-1, 1], mode='lines', line=dict(color='green', width=2), name='Средняя температура'
    ))
    fig.add_trace(go.Scatter(
        x=[lower_bound, lower_bound], y=[-1, 1], mode='lines', line=dict(color='green', width=2, dash='dash'), name='Нижняя граница'
    ))
    fig.add_trace(go.Scatter(
        x=[upper_bound, upper_bound], y=[-1, 1], mode='lines', line=dict(color='green', width=2, dash='dash'), name='Верхняя граница'
    ))
    fig.add_trace(go.Scatter(
        x=[current_temp, current_temp], y=[-1.2, 1.2], mode='lines', line=dict(color='red', width=2), name='Текущая температура'
    ))
    fig.add_trace(go.Scatter(
        x=[lower_bound, upper_bound, upper_bound, lower_bound],
        y=[-1, -1, 1, 1], fill='toself', fillcolor='rgba(0, 255, 0, 0.2)', line=dict(color='rgba(0, 0, 0, 0)'), name='Диапазон температур'
    ))

    fig.update_layout(
        xaxis=dict(range=[-40, 40], title="Температура (°C)"),
        yaxis=dict(range=[-5, 5], showticklabels=False),
        title="Диапазон температур", template="plotly_white", showlegend=True
    )

    for temp, color, pos in [(mean_temp, 'green', -1.8), (lower_bound, 'green', -1.8), (upper_bound, 'green', -1.8), (current_temp, 'red', 1.5)]:
        fig.add_annotation(
            x=temp, y=pos, text=f"{temp:.2f} °C", showarrow=False, font=dict(color=color, size=10)
        )

    st.plotly_chart(fig)

def plot_temperature_history(data, city):
    city_data = data[data['city'] == city]
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=city_data[city_data['temperature'] > city_data['rolling_avg'] + 2 * city_data['rolling_std']]['timestamp'],
        y=city_data[city_data['temperature'] > city_data['rolling_avg'] + 2 * city_data['rolling_std']]['temperature'],
        mode='markers', marker=dict(color='rgb(255, 69, 0)', size=6, opacity=0.7), name='Аномальные максимумы'
    ))

    fig.add_trace(go.Scatter(
        x=city_data[city_data['temperature'] < city_data['rolling_avg'] - 2 * city_data['rolling_std']]['timestamp'],
        y=city_data[city_data['temperature'] < city_data['rolling_avg'] - 2 * city_data['rolling_std']]['temperature'],
        mode='markers', marker=dict(color='rgb(0, 0, 255)', size=6, opacity=0.7), name='Аномальные минимумы'
    ))

    fig.add_trace(go.Scatter(
        x=city_data['timestamp'], y=city_data['rolling_avg'],
        mode='lines', line=dict(color='rgb(34, 139, 34)', width=2), name='Средняя температура'
    ))

    fig.add_trace(go.Scatter(
        x=city_data['timestamp'], y=city_data['rolling_avg'] + 2 * city_data['rolling_std'],
        mode='lines', line=dict(color='rgb(255, 69, 0)', width=2, dash='dash'), name='Аномалия макс. температуры'
    ))

    fig.add_trace(go.Scatter(
        x=city_data['timestamp'], y=city_data['rolling_avg'] - 2 * city_data['rolling_std'],
        mode='lines', line=dict(color='rgb(0, 0, 255)', width=2, dash='dash'), name='Аномалия мин. температуры'
    ))

    fig.update_layout(
        xaxis=dict(title="Дата"),
        yaxis=dict(title="Температура (°C)"),
        title=f"Исторические данные для города {city}",
        template="plotly_dark",
        showlegend=True
    )

    st.plotly_chart(fig)

def plot_monthly_temperature_trends(data, city):
    city_data = data[data['city'] == city]
    city_data['month'] = city_data['timestamp'].dt.month
    monthly_avg = city_data.groupby('month')['temperature'].mean()
    monthly_std = city_data.groupby('month')['temperature'].std()
    anomalies = city_data[abs(city_data['temperature'] - city_data['temperature'].mean()) > 2 * city_data['temperature'].std()]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=monthly_avg.index, y=monthly_avg.values, mode='lines+markers',
        name='Средняя температура по месяцам', line=dict(color='blue', width=2)
    ))

    fig.add_trace(go.Scatter(
        x=monthly_avg.index, y=monthly_avg.values + 2 * monthly_std.values, mode='lines',
        name='Верхняя граница (Среднее + 2 std)', line=dict(color='red', dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=monthly_avg.index, y=monthly_avg.values - 2 * monthly_std.values, mode='lines',
        name='Нижняя граница (Среднее - 2 std)', line=dict(color='red', dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=anomalies['timestamp'], y=anomalies['temperature'], mode='markers',
        name='Аномалии', marker=dict(color='purple', size=8)
    ))

    fig.update_layout(
        title=f"Температурные тренды по месяцам для города {city}",
        xaxis=dict(title="Месяц"),
        yaxis=dict(title="Температура (°C)"),
        template="plotly_dark",
        showlegend=True
    )

    st.plotly_chart(fig)

st.title("Анализ аномалий температуры")

df = st.file_uploader("Загрузите CSV файл с данными", type=["csv"])

if df is not None:
    df = pd.read_csv(df)
    st.write("Загруженный файл:")
else:
    st.write("Сейчас используется тестовый набор данных.")
    df = pd.read_csv("temperature_data.csv")

df = analyze_data(df)
df['timestamp'] = pd.to_datetime(df['timestamp'])

api_key = st.text_input("Введите API-ключ для OpenWeatherMap:")
city = st.selectbox("Выберите город для анализа", df['city'].unique())

st.subheader("Историческая информация и тренды")
plot_temperature_history(df, city)
plot_monthly_temperature_trends(df, city)

if st.button("Проверить текущую температуру"):
    if not api_key:
        st.error("Пожалуйста, введите API-ключ для OpenWeatherMap.")
    else:
        response = fetch_temperature(city, api_key)
        if response.status_code == 200:
            current_temp = response.json()['main']['temp']
            is_anomaly, mean_temp, std_temp = detect_temperature_anomaly(df, city, current_temp)

            st.write(f"Текущая температура в {city}: {current_temp} °C")

            if mean_temp is not None:
                if is_anomaly:
                    st.error("❌ Текущая температура аномальна.")
                else:
                    st.success("✅ Текущая температура в пределах нормы.")
                st.write(f"Средняя температура в этом месяце: {mean_temp:.2f} °C")
                st.write(f"Диапазон нормальных температур: ({mean_temp - 2 * std_temp:.2f} ; {mean_temp + 2 * std_temp:.2f}) °C")
                plot_horizontal_temperature_range(mean_temp, std_temp, current_temp)
            else:
                st.warning("❗ Нет достаточных данных для анализа.")
        else:
            st.error("❌ Ошибка при получении данных с API.")
