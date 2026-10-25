from app.llm.client import LLMClient, Message, ToolSpec

client = LLMClient()

r = client.generate([Message("user", "Say hello in 3 words.")])
print("TEXT:", r.text)

r = client.generate([Message("user", 'Return JSON {"ok": true}')], json_mode=True)
print("JSON:", r.text)

tool = ToolSpec(
    name="search_documents",
    description="Search the document collection.",
    parameters={"type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]},
)
r = client.generate([Message("user", "Who founded Science Fantasy magazine? Use the tool.")], tools=[tool])
print("TOOL CALLS:", r.tool_calls)