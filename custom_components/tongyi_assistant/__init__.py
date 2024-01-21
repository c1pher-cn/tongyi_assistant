"""The TongyiAI Conrtrol integration."""
from __future__ import annotations

import json
import re
import random

from functools import partial
import logging
from typing import Any, Literal

from string import Template

import dashscope



from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, TemplateError
from homeassistant.helpers import intent, template, entity_registry,area_registry
from homeassistant.util import ulid

from .const import (
    CONF_CHAT_MODEL,
    CONF_MAX_TOKENS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    CONF_TOP_P,
    DEFAULT_CHAT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_PROMPT,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    ENTITY_TEMPLATE,
    PROMPT_TEMPLATE,
)

_LOGGER = logging.getLogger(__name__)

entity_template = Template(ENTITY_TEMPLATE)
prompt_template = Template(PROMPT_TEMPLATE)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TongyiAI Agent from a config entry."""
    dashscope.api_key = entry.data[CONF_API_KEY]

    #try:
    #    await hass.async_add_executor_job(
    #        partial(dashscope.Generation.call(
    #            dashscope.Generation.Models.qwen_turbo,
    #            messages=messages,
    #            # set the random seed, optional, default to 1234 if not set
    #            seed=1234,
    #            result_format='message',  # set the result to be "message" format.
    #        ), request_timeout=10)
    #    )
    #except error.AuthenticationError as err:
    #    _LOGGER.error("Invalid API key: %s", err)
    #    return False
    #except error.TongyiAIError as err:
    #    raise ConfigEntryNotReady(err) from err

    conversation.async_set_agent(hass, entry, TongyiAIAgent(hass, entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload TongyiAI Agent."""
    #openai.api_key = None
    conversation.async_unset_agent(hass, entry)
    return True



def _entry_ext_dict(entry: er.RegistryEntry) -> dict[str, Any]:
    """Convert entry to API format."""
    data = entry.as_partial_dict
    data["aliases"] = entry.aliases
    data["capabilities"] = entry.capabilities
    data["device_class"] = entry.device_class
    data["original_device_class"] = entry.original_device_class
    data["original_icon"] = entry.original_icon
    return data

class TongyiAIAgent(conversation.AbstractConversationAgent):
    """TongyiAI Conrtrol Agent."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self.history: dict[str, list[dict]] = {}

    @property
    def attribution(self):
        """Return the attribution."""
        return {"name": "Powered by Tongyi", "url": "https://tongyi.aliyun.com/"}

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL
    def find_last_brace(self,s):
        last_brace_index = -1
        for i, char in enumerate(reversed(s)):
            if char == '}':
                last_brace_index = len(s) - 1 - i
                break
        if last_brace_index >= 0:
            last_brace = s[last_brace_index]
            return last_brace_index
        else:
            return -2

    async def async_generate_tongyi_call(self, model,max_tokens,top_p,temperature,sending_messages):
        try:
            # 将同步方法放入执行器（线程池）中执行
            result = await self.hass.async_add_executor_job(
                lambda: dashscope.Generation.call(
                model=model,
                #dashscope.Generation.Models.qwen_turbo,
                messages=sending_messages,
                seed=random.randint(1, 10000),
                max_tokens=max_tokens,
                top_p=top_p,
                temperature=temperature,
                result_format='message')
            )
            return result
        except Exception as exc:
            _LOGGER.error("Error occurred while calling dashscope.Generation.call: %s", exc)
            return None

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:

        """ Options input """

        raw_prompt = self.entry.options.get(CONF_PROMPT, DEFAULT_PROMPT)
        model = self.entry.options.get(CONF_CHAT_MODEL, DEFAULT_CHAT_MODEL)
        max_tokens = self.entry.options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
        top_p = self.entry.options.get(CONF_TOP_P, DEFAULT_TOP_P)
        temperature = self.entry.options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)

        """ Start a sentence """

        # check if the conversation is continuing or new


        exposed_entities = self.get_exposed_entities()
        # generate the prompt to be added to the sending messages later
        try:
            prompt = self._async_generate_prompt(raw_prompt,exposed_entities)
        except TemplateError as err:

            _LOGGER.error("Error rendering prompt: %s", err)

            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Sorry, I had a problem with my template: {err}",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        # if continuing then get the messages from the conversation history
        #历史对话
        if user_input.conversation_id in self.history:
            conversation_id = user_input.conversation_id
            messages = self.history[conversation_id]

        # if new then create a new conversation history
        #新建对话
        else:
            conversation_id = ulid.ulid()
            # add the conversation starter to the begining of the conversation
            # this is to give the assistant more personality
            messages = [{"role": "system", "content": prompt}]
            #这里的content是从raw_prompt 也就是options里设置的指令



         #prompt模版渲染，里面有设备信息和用户在组建中配置的prompt
        messages.append({"role": "user", "content": user_input.text}) #用户输入的聊天信息


        _LOGGER.info("Prompt for %s: %s", model,max_tokens,top_p,temperature, messages)

        """ TongyiAI Call """

        # NOTE: this version does not support a full conversation history
        # this is because the prompt_template and entities list
        # can quickly increase the size of a conversation
        # causing an error where the payload is too large

        # to that end we create a new list of messages to be sent
        # sending only the system role message and the current user message
        sending_messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_input.text}
        ]

        # call Tongyi
        #try:
        #    result = await self.hass.async_add_executor_job(dashscope.Generation.call(dashscope.Generation.Models.qwen_turbo,messages=sending_messages,seed=random.randint(1, 10000),result_format='message'))
       #     result = await openai.ChatCompletion.acreate(
       #         model=model,
       #         messages=sending_messages,
       #         max_tokens=max_tokens,
       #         top_p=top_p,
       #         temperature=temperature,
       #         user=conversation_id,
       #     )
       # except error.TongyiAIError as err:
       #     intent_response = intent.IntentResponse(language=user_input.language)
       #     intent_response.async_set_error(
       #         intent.IntentResponseErrorCode.UNKNOWN,
       #         f"Sorry, I had a problem talking to TongyiAI: {err}",
       #     )
       #     return conversation.ConversationResult(
       #         response=intent_response, conversation_id=conversation_id
       #     )
        result =await self.async_generate_tongyi_call(model,max_tokens,top_p,temperature, sending_messages)
        _LOGGER.error("Response for tongyi: %s", result)
        content = result["output"]["choices"][0]["message"]["content"]

        # set a default reply
        # this will be changed if a better reply is found
        reply = content
        json_response = None

        # all responses should come back as a JSON, since we requested such in the prompt_template
        try:
            json_response = json.loads(content)
        except json.JSONDecodeError as err:
            _LOGGER.info('Error on first parsing of JSON message from TongyiAI %s', err)

        # if the response did not come back as a JSON
        # attempt to extract JSON from the response
        # this is because GPT will sometimes prefix the JSON with a sentence

        start_idx = content.find('{')
        #end_idx = content.rfind('}') + 1
        end_idx = self.find_last_brace(content) + 1

        if start_idx != -1 and end_idx != -1:
            json_string = content[start_idx:end_idx]
            try:
                json_response = json.loads(json_string)
            except json.JSONDecodeError as err:
                _LOGGER.error('Error on second parsing of JSON message from TongyiAI %s', json_string)
        else:
            _LOGGER.info('Error on second extraction of JSON message from TongyiAI, %s', content)
     

        # only operate on JSON actions if JSON was extracted
        if json_response is not None:

            # call the needed services on the specific entities

            try:
                for entity in json_response["entities"]:
                    domain,device = entity['service_data']['entity_id'].split('.')
                    # TODO: make this support more than just lights
                    #await self.hass.services.async_call(device, entity['action'], {'entity_id': entity['entity_id'],'service_data': entity['service_data']})
                    #await self.hass.services.async_call(domain, entity['service'], entity['service_data'])
                    if entity['service'].find('.') > 0:
                        domain2,service=entity['service'].split('.')
		    else:
                        service=entity['service']
                    await self.hass.services.async_call(domain, service, entity['service_data'])
                    _LOGGER.error("Calling service: %s %s %s", domain, service, entity['service_data'])
            except KeyError as err:
                _LOGGER.error('该操作还不支持 %s', user_input.text)

            # resond with the "assistant" field of the json_response

            try:
                reply = json_response['assistant']
            except KeyError as err:
                _LOGGER.error('Error extracting assistant response %s', user_input.text)
                intent_response = intent.IntentResponse(language=user_input.language)
                intent_response.async_set_error(
                    intent.IntentResponseErrorCode.UNKNOWN,
                    f"Sorry, there was an error understanding TongyiAI: {err}",
                )
                return conversation.ConversationResult(
                    response=intent_response, conversation_id=conversation_id
                )

        messages.append(reply)
        #messages.append(result["choices"][0]["message"])
        self.history[conversation_id] = messages

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(reply)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    def _async_generate_prompt(self, raw_prompt: str, exposed_entities) -> str:
        """Generate a prompt for the user."""
        return template.Template(raw_prompt, self.hass).async_render(
            {
                "ha_name": self.hass.config.location_name,
                "exposed_entities": exposed_entities,
            },
            parse_result=False,
        )

    def get_exposed_entities(self):
        states = [
            state
            for state in self.hass.states.async_all()
            if async_should_expose(self.hass, conversation.DOMAIN, state.entity_id)
        ]
        registry = entity_registry.async_get(self.hass)
        exposed_entities = []
        '''
        方法1
        areas = area_registry.async_list_areas()
        for area in areas:
            entities = []
            entities = await self.hass.states.async_select_area(area)
            for entity in entities:
                entities.append(
                {
                    "entity_id": entity.entity_id,
                    "name": entity.friendly_name,
                    "state": self.hass.states.get(entity.entity_id).state,
                    "aliases": entity.aliases,
                }
                )
            exposed_entities.append(
            {
                "area_name":area,
                "entities",entities
            })

        方法2
        areas = self.hass.async_list_areas()
        for area in areas:
            entities = []
            for state in states:
            if 'area_name' in state.context:

                exposed_entities.append((state.entity_id, state.context.area_name))

        方法3
        area_reg = area_registry.async_get(hass)
        return [area.id for area in area_reg.async_list_areas()]

        area_reg.async_list_areas()
        if area := area_reg.async_get_area(area_id)
            area.name
        area_name()

        exposed_entities = []


        '''
        for state in states:
            entity_id = state.entity_id
            entity = registry.entities.get(entity_id)

            aliases = []
            if entity and entity.aliases:
                aliases = entity.aliases

            exposed_entities.append(
                {
                    "entity_id": entity_id,
                    "name": state.name,
                    "state": self.hass.states.get(entity_id).state,
                    "aliases": aliases,
                }
            )
        return exposed_entities
