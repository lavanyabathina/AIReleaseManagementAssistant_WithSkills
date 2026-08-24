from langchain_core.messages import AIMessage, ToolMessage


class ToolCall:
    """
    One tool the agent called, together with whatever that tool returned.

    The agent decides to call a tool in one message, and the tool's answer
    arrives in a later message. This class holds both halves in one place.
    """

    def __init__(self, name, args, id=None, output=None):
        self.name = name
        self.args = args
        self.id = id
        self.output = output

    @property
    def failed(self):
        """
        True when the tool returned an error instead of a result.

        Our tools report problems by returning {"error": "..."} rather than
        raising, so we look for that key in the output.
        """
        if self.output is None:
            return False

        return "'error':" in self.output or '"error":' in self.output

    def __repr__(self):
        return f"ToolCall(name={self.name!r}, failed={self.failed})"


class AgentResponse:
    """
    The result of running the agent.

    agent.invoke() hands back a plain list of messages. This class wraps
    that list and offers small methods to pull out the parts you usually
    want, so callers do not have to walk the messages themselves.
    """

    def __init__(self, messages=None):
        self.messages = messages if messages is not None else []

    def ai_messages(self):
        """Every message the model produced."""
        found = []

        for message in self.messages:
            if isinstance(message, AIMessage):
                found.append(message)

        return found

    def tool_outputs(self):
        """
        Map each tool call id to the text that tool returned.

        Used to match a tool's answer back to the call that asked for it.
        """
        outputs = {}

        for message in self.messages:
            if isinstance(message, ToolMessage):
                outputs[message.tool_call_id] = message.text

        return outputs

    def tool_calls(self):
        """Every tool call the agent made, each paired with its output."""
        outputs = self.tool_outputs()
        calls = []

        for message in self.ai_messages():
            for call in message.tool_calls:
                call_id = call.get("id")

                calls.append(
                    ToolCall(
                        name=call["name"],
                        args=call["args"],
                        id=call_id,
                        output=outputs.get(call_id),
                    )
                )

        return calls

    def failed_calls(self):
        """Only the tool calls that returned an error."""
        failed = []

        for call in self.tool_calls():
            if call.failed:
                failed.append(call)

        return failed

    def final_output(self):
        """
        The agent's final answer.

        Walks backwards through the AI messages and returns the first one
        that actually contains text. Uses the message .text property, which
        LangChain normalizes across providers, so Claude content blocks,
        Gemini parts and plain strings all work.
        """
        for message in reversed(self.ai_messages()):
            text = message.text.strip()

            if text:
                return text

        return None

    def print_report(self):
        """Print what the agent did, and what it concluded."""
        print("\n==============================")
        print("AGENT ACTIONS")
        print("==============================")

        for call in self.tool_calls():
            print(f"\nAction: {call.name}")
            print(f"Arguments: {call.args}")

            if call.output is not None:
                print(f"Tool Output: {call.output}")

        failed = self.failed_calls()

        if failed:
            print("\n==============================")
            print(f"TOOL FAILURES ({len(failed)})")
            print("==============================")

            for call in failed:
                print(f"\n{call.name}: {call.output}")

        print("\n==============================")
        print("FINAL AGENT OUTPUT")
        print("==============================")
        print(self.final_output() or "(no final AI message)")
