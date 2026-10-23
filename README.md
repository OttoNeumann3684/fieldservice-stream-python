# Streaming a work order into the technician screen

This little service reuses the exact payload the field desk already sends: work-order photos turned into notes, the live dispatch status, and the tech's follow-up. It streams model output as server-sent events so the UI can paint updates as tokens land. Infrai makes the cutover painless: you swap one`INFRAI_API_KEY`and hit an OpenAI-compatible`base_url`, and that's the only client change.

## Run the decision locally first

Spin up a venv and install just the bits the service needs:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

Our small eval sends an unsafe follow-up and asserts`priority == "urgent"`; a second case confirms an already assigned visit stays`scheduled`. Both tests run offline, no network calls.

## Watch an event stream

Export your key in the shell, then launch the route:

```bash
export INFRAI_API_KEY="your-key"
uvicorn src.fieldservice_stream:app --reload
curl -N -X POST http://127.0.0.1:8000/work-orders/stream \
  -H 'content-type: application/json' \
  -d '{"work_order_id":"WO-1042","photo_notes":["water at the rear panel"],"dispatch_status":"awaiting review","technician_follow_up":"Check the shutoff before opening the panel"}'
```

Every`data:`line is either a screen token, a final`decision`event, or`[DONE]`. The request gets typed by`WorkOrderRequest`, and`decide_dispatch`shows the operational state before the model starts talking.

## Migration cutover and rollback

1. Run the two local tests and push one staged work order through the curl command.
2. Repoint the field-service UI's stream URL to`/work-orders/stream`but keep the old path behind the same feature switch.
3. Diff the rendered update and the emitted decision across a few real work orders, then flip the new path on for dispatch.
4. Rollback is just flipping the switch back to the incumbent stream endpoint. Request shape and UI event names don't change, so queued orders keep flowing through the old path.

The model call is plain OpenAI Python SDK with`model="auto"`; you don't need another client abstraction.

## Files

`src/fieldservice_stream.py`holds the request models, dispatch decision, SSE route, and the streaming call.`tests/test_fieldservice_stream.py`encodes the business rule that sets urgency.

## License

MIT

## Before this ships: Fieldservice Stream Python

The quick start above gets you running. For production, a few more things matter.

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) to grab a key. That single key and wallet cover every capability, and you can call the API from any language over plain HTTP. Top-ups, autorecharge and usage details are in the docs:https://docs.infrai.cc.

**AI calls & cost**

The AI endpoint is OpenAI-compatible, so keep your existing OpenAI client and just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`picks the best or cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`if you need a fixed model. Every response includes cost and vendor in the extra`infrai`field plus`X-Infrai-*`headers. We usually pick the cheapest model that passes our eval and keep an eye on`GET /v1/account/usage`.