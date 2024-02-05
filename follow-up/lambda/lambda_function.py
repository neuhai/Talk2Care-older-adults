# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.


# This is the skill that Alexa does follow up for the nurse
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response


import os 
import openai
import time
from dotenv import load_dotenv

load_dotenv()

import json
import gspread
sheet_url = "your_sheet_url" # change to your sheet url
gc = gspread.service_account(filename = 'credentials.json')
sh = gc.open_by_url(sheet_url)

worksheet = sh.get_worksheet(0)
worksheet.update_cell(1,2, "follow up connected") #Write this message in first row and first column

# ==== configure OpenAI ====
openai.api_key = os.getenv("OPENAI_API_KEY")


COMMON_SETUP = """
This is the basic patient profile:
Name: John Smith
Age: 75
Location: Boston, MA
Health Conditions: Hypertension, Mild Arthritis
Living Situation: Lives alone in an apartment, has a caregiver who visits twice a week
    
"""

SCENARIO_A = """

Post-Surgery Follow-up Scenario:
After a small surgery, John Smith has returned home. He's experiencing discomfort and has questions about his recovery. \
You should check on his pain level, wound healing, and medication adherence, and let him know that you will give this information to the nurse. \

To lead a conversation for a regular check up, the questions includes the following. Make sure that you only ask one question at a time. \
Checkup questions:\
1. how the patient is feeling overall\
2. ask about the patient's disease condition,\ 
for example, for people who has hypertension, you may ask about blood pressure\
for people who has diabetes, you may ask about blood glutose level\
for people who went through surgery or accidents, you can ask how they are recovering, 
for people experiencing pain, you can ask about their pain level, rate from 1 to 10, etc.\
3. has the previous syptoms improved or not\

Medication: \
1. whether the patient is taking the medication according to instruction\
2. whether the patient is taking any extra medication\


"""


INSTRUCTIONS = """General: \
You are Follow Up Assistant, an automated service that help healthcare providers connect with their patients, especially older adults.\
Your main job is to talk with patients to collecting their information during their recovery and rehabilitation after a surgery, \
and help patients ask questions to providers.\
You will support the asynchronous patient-provider communication and save time and effort for providers.\
You speak in a brief, friendly and easy to understand way, like a clinician would do when they talk to older adults.\
Each response should be within 20 words. Do not introduce yourself twice.

Overview: \
You must guide and lead this conversation. During your first conversation, after the patient says hello, you should \
1. greet the patient and introduce yourself \ 
2. Conduct your main task given below. If you are following up with the patient, \
you should start by asking the first check up question, and then ask questions one by one.\ 
2. Ask if the patient has any more questions or anything else you can help with \

Make sure to clarify all systoms professionally.

"""


SHORT_INSTRUCTION = """Don't say more than 20 words. Ask follow up questions if necessary.\
    Don't ask questions that you already have the answers.\
    If there is anything that you think the patient should consult the healthcare provider, you should ask not give any suggestions directly.\
    Instead, you can help pass this information to the doctor, and you can tell him that either you or the doctor will get back to him.
    Remember that your capabilities are limited, for example, you cannot directly arrange an appointment 
    or give medical diagnosis.\
    Do not repeat yourself too much, unless it is necessary.
    """
TEMPERATURE = 0.8
MAX_TOKENS = 512
FREQUENCY_PENALTY = 0
PRESENCE_PENALTY = 0.2

MAX_CONTEXT_QUESTIONS = 20



logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def process_question(handler_input):
    
    intent_name = ask_utils.get_intent_name(handler_input)
    separated_intent_name = intent_name.split("Intent")[0]
    new_question = ""

    if intent_name == "QuestionIntent":
        new_question = "How/what/why/when/Is/Can/who/Do "
    elif intent_name == "StartWithI":
        new_question = "I/My"
    elif intent_name == "YesResponse":
        new_question = "Yes(positive response) "
    elif intent_name == "NoResponse":
        new_question = "No(negative response) "
    elif intent_name == "Amazon.ByeIntent":
        # new_question = "Bye"
        return (handler_input.response_builder
        .speak("Bye")
        .response)
    
    if (handler_input.request_envelope.request.intent.slots["response"].value):
        return new_question + handler_input.request_envelope.request.intent.slots["response"].value
    return new_question

def API_request(new_question):
    user_questions = worksheet.col_values(1)
    va_responses = worksheet.col_values(2)
    CHAT_HISTORY = []
    chat_history_filtered = list(filter(lambda x: not None, worksheet.col_values(1)))
    # print(user_questions)
    if len(user_questions) < 2:
        # this function writes to a cell in the spreadsheet
        worksheet.update("A2", "User Questions")
        worksheet.update("B2", "VA responses")
    else:
        new_index = str(len(chat_history_filtered) + 1)
        worksheet.update("A" + new_index, new_question)
        for i in range(1, len(user_questions)-2):
            CHAT_HISTORY.append((user_questions[i], va_responses[i]))
    
    # print("hey")
    # print(CHAT_HISTORY)
    messages = [
        {"role": "system", "content": INSTRUCTIONS + COMMON_SETUP + SCENARIO_A }
    ]

    for question, answer in CHAT_HISTORY[-MAX_CONTEXT_QUESTIONS:]:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": answer})


    messages.append({ "role": "user", "content": new_question })
    messages.append({"role": "system", "content": SHORT_INSTRUCTION })
    # print(messages)
        
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        top_p=1,
        frequency_penalty=FREQUENCY_PENALTY,
        presence_penalty=PRESENCE_PENALTY,
    )

    while completion == '':
        time.sleep(3)

    # get the response and remove the logic (Step X : ...)
    response = completion.choices[0].message.content
    # final_response = response.split(":")[-1]
    
    # response = completion.choices[0].message.content
    # print(response)
    new_index = str(len(chat_history_filtered) + 1)
    worksheet.update("A" + new_index, new_question)
    worksheet.update("B" + new_index, response)
    return response


def get_GPT_response(handler_input):
    
    new_question = process_question(handler_input)
    # print(new_question, response)
    # CHAT_HISTORY.append((completion.choices[0].message.role, completion.choices[0].message.content))
    return API_request(new_question)

def to_speech(handler_input, response):
    break_audio = " <break time=\"10s\" /> "
    sound_bank_audio = "<prosody volume='silent'> . </prosody>"
    # speak_output = response + break_audio*18 + sound_bank_audio
    speak_output = response
    ask_output =  "Anything else I can help? You can begin the sentence with Alexa" + break_audio*3 + sound_bank_audio

    return (
        handler_input.response_builder
        .speak(speak_output)
        .ask(ask_output)
        .response
    )

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        chat_history_filtered = list(filter(lambda x: not None, worksheet.col_values(1)))
        new_index = str(len(chat_history_filtered)+1)

        # worksheet.update("A", "Participant #") #Write this message in first row and first column
        worksheet.update("A" + new_index, "Follow Up Start")
        # response = get_GPT_response(handler_input)
        new_question = "Hello?"
        response = API_request(new_question)
        return to_speech(handler_input, response)

class AskChatGPTIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AskChatGPTIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        response = get_GPT_response(handler_input)
        return to_speech(handler_input, response)

class StartWithIHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("StartWithI")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        response = get_GPT_response(handler_input)
        
        return to_speech(handler_input,response)

class YesResponseHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("YesResponse")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        response = get_GPT_response(handler_input)

        return to_speech(handler_input,response)

class NoResponseHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("NoResponse")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        response = get_GPT_response(handler_input)

        return to_speech(handler_input,response)

class ByeIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.ByeIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # new_question = "Bye"
        # if (handler_input.request_envelope.request.intent.slots["response"].value): 
        #     new_question = "Bye(negative response), " + handler_input.request_envelope.request.intent.slots["response"].value
        
        # response = get_GPT_response( new_question)
        response = get_GPT_response(handler_input)

        return (
            handler_input.response_builder
                .speak(response)
                .response
        )


class QuestionIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("QuestionIntent")(handler_input))

    def handle(self, handler_input):

        response = get_GPT_response(handler_input)

        return to_speech(handler_input,response)

class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # speak_output = "You can say hello to me! How can I help?"
        speak_output ="You can say hello or help."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("Sorry, I didn't hear you clearly. Could you please say that again?")
                .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        # speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        speech = "Sorry, I didn't hear you clearly. Could you please say that again?"
        # reprompt = "Sorry, I didn't hear you clearly. Could you please say that again?"

        return handler_input.response_builder.speak(speech).ask(speech).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.
        speech = "Sorry, I didn't hear you clearly. SessionEndedRequest"
        return handler_input.response_builder.speak(speech).response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "Sorry, I didn't hear you clearly. Could you please say that again?"
        reprompt = "I didn't catch that. What can I help you with?"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, can you say bye and start again?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AskChatGPTIntentHandler())
sb.add_request_handler(StartWithIHandler())
sb.add_request_handler(YesResponseHandler())
sb.add_request_handler(NoResponseHandler())
sb.add_request_handler(QuestionIntentHandler())
sb.add_request_handler(ByeIntentHandler())

sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()