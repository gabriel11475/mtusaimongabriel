from automata.tm.dtm import DTM
from fastapi import FastAPI, Request, Depends
from fastapi_mail import ConnectionConfig, MessageSchema, MessageType, FastMail
from sqlalchemy.orm import Session
import json
from sql_app import crud, models, schemas
from sql_app.database import engine, SessionLocal
from util.email_body import EmailSchema
import pika
from prometheus_fastapi_instrumentator import Instrumentator
import asyncio
models.Base.metadata.create_all(bind=engine)

conf = ConnectionConfig(
    MAIL_USERNAME="1cada09aba3b38",
    MAIL_PASSWORD="839678f967766f",
    MAIL_FROM="from@example.com",
    MAIL_PORT=587,
    MAIL_SERVER="sandbox.smtp.mailtrap.io",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)

app = FastAPI()

Instrumentator().instrument(app).expose(app)

listresult = []

# Patter Singleton
# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

channel = None


@app.get("/get_history/{id}")
async def get_history(id: int, db: Session = Depends(get_db)):
    history = crud.get_history(db=db, id=id)
    if history is None:
        return {
            "code": "404",
            "msg": "not found"
        }
    return history


@app.get("/get_all_history")
async def get_all_history(db: Session = Depends(get_db)):
    history = crud.get_all_history(db=db)
    return history

async def processDtm(info: Request, db: Session = Depends(get_db)):
    
    #info = await info.json()
    info = info.json
    states = set(info.get("states", []))

    if len(states) == 0:
        return {
            "code": "400",
            "msg": "states cannot be empty"
        }
    input_symbols = set(info.get("input_symbols", []))
    if len(input_symbols) == 0:
        return {
            "code": "400",
            "msg": "input_symbols cannot be empty"
        }
    tape_symbols = set(info.get("tape_symbols", []))
    if len(tape_symbols) == 0:
        return {
            "code": "400",
            "msg": "tape_symbols cannot be empty"
        }

    initial_state = info.get("initial_state", "")
    if initial_state == "":
        return {
            "code": "400",
            "msg": "initial_state cannot be empty"
        }
    blank_symbol = info.get("blank_symbol", "")
    if blank_symbol == "":
        return {
            "code": "400",
            "msg": "blank_symbol cannot be empty"
        }
    final_states = set(info.get("final_states", []))
    if len(final_states) == 0:
        return {
            "code": "400",
            "msg": "final_states cannot be empty"
        }
    transitions = dict(info.get("transitions", {}))
    if len(transitions) == 0:
        return {
            "code": "400",
            "msg": "transitions cannot be empty"
        }

    input = info.get("input", "")
    if input == "":
        return {
            "code": "400",
            "msg": "input cannot be empty"
        }

    dtm = DTM(
        states=states,
        input_symbols=input_symbols,
        tape_symbols=tape_symbols,
        transitions=transitions,
        initial_state=initial_state,
        blank_symbol=blank_symbol,
        final_states=final_states,
    )
    if dtm.accepts_input(input):
        print('accepted')
        result = "accepted"
    else:
        print('rejected')
        result = "rejected"
    
    history = schemas.History(query=str(info), result=result)
    crud.create_history(db=db, history=history)

    return result

def on_message(channel, method_frame, header_frame, body):
    json_data = json.loads(body)
    listresult.append(processDtm(json_data))
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)

def send_json_to_queue(json_data):
    channel.basic_publish(exchange='', routing_key='json_queue', body=json.dumps(json_data))

@app.post("/dtm")
async def dtm(info: Request, db: Session = Depends(get_db)):
    listresult = []
    connection = pika.BlockingConnection()
    channel = connection.channel()
    channel.queue_declare(queue='json_queue')
    batch_data = await info.json
    if isinstance(batch_data, list):
        for json_data in batch_data:
            send_json_to_queue(json_data)
    else:
        return {
            "code": "400",
            "msg": "Json Batch is empty cannot be empty"
        }
    channel.basic_consume('json_queue', on_message)
    channel.start_consuming()

    info = await info.json()

    finalresult = ""
    for r in listresult:
        finalresult+= r +"\n"
    email_shema = EmailSchema(email=["to@example.com"])

    await simple_send(email_shema, result=finalresult, configuration=str(info))
    
    return {
        "code": listresult != [] and "200" or "400",
        "msg": listresult != [] and "Success" or "Failed"
    }


async def simple_send(email: EmailSchema, result: str, configuration: str):
    html = """
    <p>Thanks for using Fastapi-mail</p>
    <p> The result is: """ + result + """</p>
    <p> We have used this configuration: """ + configuration + """</p>
    """
    message = MessageSchema(
        subject="Fastapi-Mail module",
        recipients=email.dict().get("email"),
        body=html,
        subtype=MessageType.html)

    fm = FastMail(conf)
    await fm.send_message(message)
    return "OK"

class Object(object):
    pass
class RequestMock:
    def __init__(self, json_data):
        self.json_data = json_data
    async def json(self):
        return self.json_data
async def main():
    dicio = {
                "input": "0011",
                "states": [
                    "q0",
                    "q1",
                    "q2",
                    "q3",
                    "q4"
                ],
                "input_symbols": [
                    "0",
                    "1"
                ],
                "tape_symbols": [
                    "0",
                    "1",
                    "x",
                    "y",
                    "."
                ],
                "initial_state": "q0",
                "blank_symbol": ".",
                "final_states": [
                    "q4"
                ],
                "transitions": {
                    "q0": {
                    "0": [
                        "q1",
                        "x",
                        "R"
                    ],
                    "y": [
                        "q3",
                        "y",
                        "R"
                    ]
                    },
                    "q1": {
                    "0": [
                        "q1",
                        "0",
                        "R"
                    ],
                    "1": [
                        "q2",
                        "y",
                        "L"
                    ],
                    "y": [
                        "q1",
                        "y",
                        "R"
                    ]
                    },
                    "q2": {
                    "0": [
                        "q2",
                        "0",
                        "L"
                    ],
                    "x": [
                        "q0",
                        "x",
                        "R"
                    ],
                    "y": [
                        "q2",
                        "y",
                        "L"
                    ]
                    },
                    "q3": {
                    "y": [
                        "q3",
                        "y",
                        "R"
                    ],
                    ".": [
                        "q4",
                        ".",
                        "R"
                    ]
                    }
                }
            }
    #jsont=  json.dumps(dicio)
    json_objects_batch = []
    json_objects_batch.append(dicio)
    newdicio = dicio
    json_objects_batch.append(newdicio)
    jsonteste = RequestMock(json_objects_batch)
    db = get_db()
    str = await dtm(json_objects_batch, db)
    print(str)

asyncio.run(main())