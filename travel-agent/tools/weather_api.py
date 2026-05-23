import datetime
from typing import Optional

import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="智能天气助手",
    description="提供实时天气查询、天气预报和穿衣建议的 API 工具，可被 Dify 等平台通过 OpenAPI Schema 导入调用。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://wttr.in"
HEADERS = {"User-Agent": "curl/7.68.0"}


class CurrentWeatherResponse(BaseModel):
    location: str = "城市名"
    country: str = "国家"
    temperature_c: int = 0
    feels_like_c: int = 0
    weather: str = "天气描述"
    humidity: int = 0
    wind_speed_kmph: int = 0
    wind_direction: str = "风向"
    visibility_km: int = 0
    uv_index: str = "紫外线指数"
    precipitation_mm: str = "降水量"
    clothing_advice: str = "穿衣建议"
    summary: str = "自然语言摘要"


class ForecastDay(BaseModel):
    date: str = "日期"
    weekday: str = "星期"
    max_temp_c: int = 0
    min_temp_c: int = 0
    avg_temp_c: int = 0
    precipitation_mm: str = "降水量"
    sun_hours: str = "日照时长"
    uv_index: str = "紫外线指数"
    activity_suggestion: str = "活动建议"


class ForecastResponse(BaseModel):
    location: str = "城市名"
    country: str = "国家"
    forecasts: list[ForecastDay] = []
    summary: str = "自然语言摘要"


def _fetch_weather(location: str, lang: str = "zh") -> Optional[dict]:
    try:
        url = f"{BASE_URL}/{location}?format=j1&lang={lang}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"DEBUG: Received data keys: {list(data.keys())}")
        if "weather" in data:
            print(f"DEBUG: weather data count: {len(data['weather'])}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fetch weather failed - {e}")
        return None


def _clothing_advice(temp_c: int, weather: str, uv: str) -> str:
    advices = []
    if temp_c >= 35:
        advices.append("🥵 高温天气，注意防暑降温，穿轻薄透气衣物")
    elif temp_c >= 28:
        advices.append("☀️ 天气炎热，注意防晒补水，建议穿短袖")
    elif temp_c >= 22:
        advices.append("🌤️ 天气温和，建议穿薄长袖或短袖搭配薄外套")
    elif temp_c >= 15:
        advices.append("🌥️ 天气微凉，建议穿长袖搭配薄外套或毛衣")
    elif temp_c >= 5:
        advices.append("🥶 天气较冷，建议穿厚外套、毛衣，搭配围巾")
    else:
        advices.append("❄️ 天气严寒，建议穿羽绒服、戴帽子手套围巾")
    if "雨" in weather:
        advices.append("🌧️ 有雨，记得带伞！")
    if "雪" in weather:
        advices.append("🌨️ 有雪，注意路滑，穿防滑鞋")
    if "雾" in weather or "霾" in weather:
        advices.append("🌫️ 能见度低，建议戴口罩")
    try:
        if int(uv) >= 6:
            advices.append("🔆 紫外线较强，建议涂抹防晒霜")
    except (ValueError, TypeError):
        pass
    return "；".join(advices)


def _activity_suggestion(avg_temp: int, precip: float) -> str:
    if precip > 5:
        return "不建议户外活动，适合室内运动或阅读"
    if avg_temp >= 35:
        return "高温天气，适合游泳等水上活动"
    if 20 <= avg_temp <= 28 and precip < 2:
        return "天气宜人，非常适合户外跑步、骑行或郊游"
    if 10 <= avg_temp < 20 and precip < 2:
        return "天气凉爽，适合散步或轻度户外运动"
    return "天气不太适合户外活动，建议室内休闲"


WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _get_weekday(date_str: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return WEEKDAYS[dt.weekday()]
    except ValueError:
        return "未知"


@app.get(
    "/weather/current",
    summary="查询当前天气",
    description="根据城市名称查询当前实时天气状况，包括温度、湿度、风力、穿衣建议等。适用于 Dify Agent 调用。",
    response_model=CurrentWeatherResponse,
    tags=["天气查询"],
)
def get_current_weather(
    location: str = Query(..., description="城市名称，如：北京、Tokyo、New York"),
):
    data = _fetch_weather(location)
    if not data:
        return CurrentWeatherResponse(
            location=location,
            summary=f"获取 {location} 天气数据失败，请检查城市名称是否正确",
        )

    current = data["current_condition"][0]
    area = data["nearest_area"][0]

    area_name = area.get("areaName", [{}])[0].get("value", location)
    country = area.get("country", [{}])[0].get("value", "")
    weather_desc = current.get("lang_zh", [{}])[0].get(
        "value", current.get("weatherDesc", [{}])[0].get("value", "未知")
    )
    temp_c = int(current["temp_C"])
    feels_like = int(current["FeelsLikeC"])
    humidity = int(current["humidity"])
    wind_speed = int(current["windspeedKmph"])
    wind_dir = current.get("winddir16Point", "N/A")
    visibility = int(current["visibility"])
    uv = current.get("uvIndex", "N/A")
    precip = current.get("precipMM", "0")

    clothing = _clothing_advice(temp_c, weather_desc, uv)

    summary = (
        f"{area_name}（{country}）当前天气：{weather_desc}，"
        f"温度 {temp_c}°C（体感 {feels_like}°C），"
        f"湿度 {humidity}%，风速 {wind_speed}km/h {wind_dir}。"
        f"{clothing}"
    )

    return CurrentWeatherResponse(
        location=area_name,
        country=country,
        temperature_c=temp_c,
        feels_like_c=feels_like,
        weather=weather_desc,
        humidity=humidity,
        wind_speed_kmph=wind_speed,
        wind_direction=wind_dir,
        visibility_km=visibility,
        uv_index=uv,
        precipitation_mm=precip,
        clothing_advice=clothing,
        summary=summary,
    )


@app.get(
    "/weather/forecast",
    summary="查询天气预报",
    description="根据城市名称查询未来最多3天的天气预报，包括每日最高/最低温、降水、活动建议等。适用于 Dify Agent 调用。",
    response_model=ForecastResponse,
    tags=["天气查询"],
)
def get_weather_forecast(
    location: str = Query(..., description="城市名称，如：北京、Tokyo、New York"),
    days: int = Query(3, ge=1, le=3, description="预报天数，1-3天"),
):
    data = _fetch_weather(location)
    if not data:
        return ForecastResponse(
            location=location,
            summary=f"获取 {location} 天气预报失败，请检查城市名称是否正确",
        )

    try:
        area = data["nearest_area"][0]
        area_name = area.get("areaName", [{}])[0].get("value", location)
        country = area.get("country", [{}])[0].get("value", "")

        # 检查 weather 数据是否存在
        if "weather" not in data or not data["weather"]:
            return ForecastResponse(
                location=area_name,
                country=country,
                summary=f"{area_name}（{country}）暂无天气预报数据",
            )

        forecasts = []
        for day in data["weather"][:days]:
            date_str = day.get("date", "")
            max_t = int(day.get("maxtempC", "0") or "0")
            min_t = int(day.get("mintempC", "0") or "0")
            avg_t = int(day.get("avgtempC", "0") or "0")
            precip = day.get("totalprecipMM", day.get("precipMM", "0"))
            sun_h = day.get("sunHour", "N/A")
            uv = day.get("uvIndex", "N/A")
            weekday = _get_weekday(date_str)
            activity = _activity_suggestion(avg_t, float(precip or "0"))

            forecasts.append(
                ForecastDay(
                    date=date_str,
                    weekday=weekday,
                    max_temp_c=max_t,
                    min_temp_c=min_t,
                    avg_temp_c=avg_t,
                    precipitation_mm=precip,
                    sun_hours=sun_h,
                    uv_index=uv,
                    activity_suggestion=activity,
                )
            )

        summary_parts = [f"{area_name}（{country}）天气预报："]
        for f in forecasts:
            summary_parts.append(
                f"{f.date}（{f.weekday}）{f.min_temp_c}°C~{f.max_temp_c}°C，"
                f"降水 {f.precipitation_mm}mm。{f.activity_suggestion}"
            )

        return ForecastResponse(
            location=area_name,
            country=country,
            forecasts=forecasts,
            summary="；".join(summary_parts),
        )
    except Exception as e:
        print(f"ERROR: Parse forecast failed - {e}")
        return ForecastResponse(
            location=location,
            summary=f"解析 {location} 天气预报数据时出错: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)