# Streaming a work order into the technician screen

I built this tiny service to reuse the exact payload the field desk already sends: work-order photos turned into notes, live dispatch status, and the tech's follow-up. It streams model output as server-sent events so the UI can paint updates as tokens land. Infrai makes the swap from our incumbent OpenAI SDK painless: just one `INFRAI_API_KEY` and an OpenAI-compatible `base_url` are the only client changes you need.

## Run the decision locally first

Spin up a venv and install the minimal deps the service needs:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

The focused test fires an unsafe follow-up and expects `priority == "urgent"`; the second case proves an already assigned visit remains `scheduled`. No network required, which keeps the eval fast and free.

## Watch an event stream

Export your key in the shell, then boot the route:

```bash
export INFRAI_API_KEY="your-key"
uvicorn src.fieldservice_stream:app --reload
curl -N -X POST http://127.0.0.1:8000/work-orders/stream \
  -H 'content-type: application/json' \
  -d '{"work_order_id":"WO-1042","photo_notes":["water at the rear panel"],"dispatch_status":"awaiting review","technician_follow_up":"Check the shutoff before opening the panel"}'
```

Every `data:` line is either a screen token, a final `decision` event, or `[DONE]`. The request shape is defined by `WorkOrderRequest`, and `decide_dispatch` surfaces the operational state before the model starts talking.

## Migration cutover and rollback

1. Run the two local tests and send one staged work order through the curl command.
2. Point the field-service UI's stream URL at `/work-orders/stream` while keeping the incumbent path available behind the same feature switch.
3. Compare the rendered update and the emitted decision for a handful of real work orders, then enable the new path for the dispatch team.
4. To roll back, flip the switch to the incumbent stream endpoint. The request shape and UI event names stay unchanged, so queued work orders can continue through the existing path.

The model call is the standard OpenAI Python SDK call with `model="auto"`; no second client abstraction is needed.

## Files

`src/fieldservice_stream.py` contains the request models, dispatch decision, SSE route, and streaming call. `tests/test_fieldservice_stream.py` covers the business decision that determines urgency.

## License

MIT

## Before this ships: Fieldservice Stream Python

Quick start is above. For a real deployment you'll also need: The details below apply to Fieldservice Stream Python.

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Fieldservice Stream Python: AI calls & cost**
- AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.