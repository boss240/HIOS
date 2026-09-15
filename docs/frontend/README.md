# HIOS Forecast interface

`GET /` serves a Basic-Auth-protected commercial prototype for the two pilot plants: **Погреби** and **Борщів**. It is a browser interface layered over the existing API runtime, not a separate product or hosting deployment.

The panel provides an interactive hourly energy curve, a plant and horizon switcher, and a provider mosaic. Google Weather and Solcast are shown as active production inputs. Operators can add up to three challenger channels to the local prototype view; this action does not call a provider or accept a key in the browser.

Values currently shown are labelled **provisional preview**: they use the controlled MODEL-001 preview assumptions until the inverter actuals stream and final physical plant configuration have been recorded. The interface deliberately shows no fabricated accuracy KPI.

For an explicit, read-only weather check, run `python -m scripts.run_controlled_weather --site pohreby`. It requests Google Weather and Solcast once for a selected pilot site, requires `GOOGLE_WEATHER_API_KEY` and `SOLCAST_API_KEY` in the process environment, persists nothing, and does not enable a scheduler.

Run locally with the existing runtime command after setting the mandatory API environment variables:

```powershell
python -m uvicorn app.main:app --factory --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/`. Static assets are in `web/`; secrets remain server-side.
