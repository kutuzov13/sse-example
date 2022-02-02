import os
import asyncio
import requests
import uvicorn
import uuid

from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse
from fastapi.responses import JSONResponse

app = FastAPI()


def get_current_data_stamp() -> dict:
    """Fetches ISS pose data from an api and returns the data in json format."""
    api_iss_url = 'https://api.wheretheiss.at/v1/satellites/25544'
    response = requests.get(api_iss_url)
    return response.json()


def is_iss_above_water(lat: float, lon: float) -> bool:
    """Checks if the ISS is currently above water."""
    secret_key = os.getenv("SECRET_KEY")
    api = f'https://api.opencagedata.com/geocode/v1/json?q={lat}+{lon}&key={secret_key}'
    response = requests.get(api).json()

    return response['results'][0]['components']['_category'] == 'natural/water'


@app.get('/located')
async def located():
    location_data = get_current_data_stamp()
    location_data['above_water'] = is_iss_above_water(
        location_data['latitude'], location_data['longitude']
    )

    return JSONResponse(content=location_data)


@app.get('/stream')
async def stream(request: Request):
    async def event():
        while True:
            if await request.is_disconnected():
                break

            result = get_current_data_stamp()
            if is_iss_above_water(result['latitude'], result['longitude']):
                yield {
                    'id': uuid.uuid4().hex,
                    'retry': 1500,
                    'data': result
                }

                await asyncio.sleep(1)

    return EventSourceResponse(event())


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", debug=False)
