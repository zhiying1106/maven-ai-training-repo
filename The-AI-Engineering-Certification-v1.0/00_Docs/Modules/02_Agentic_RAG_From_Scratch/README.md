# Module 2: 🔁 Agentic RAG From Scratch

🎯 **Goal**: Understand what an “agent” is and look under the hood of agentic RAG and the create_agent abstraction

📚 **Learning Outcomes**

- Understand agents and the foundational agent loop
- Learn the key components of building agents in LangChain 1.0
- Learn the core constructs of low-level orchestration using LangGraph
- Understand how to set up tracing, view traces, and monitor performance

🧰 **New Tools**

- Orchestration: [LangChain](https://docs.langchain.com/oss/python/langchain/overview), [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)
- Vector Database: [QDrant](https://github.com/qdrant)
- Monitoring: [LangSmith Observability](https://docs.langchain.com/langsmith/observability)

## 📛 Required Tooling & Account Setup

In addition to the tools we've already learned, in this module you'll need:

1. Create a [LangSmith](https://smith.langchain.com/) account

## 📜 Recommended Reading

1. [ReAct](https://arxiv.org/abs/2210.03629): Synergizing Reasoning and Acting in Language Models (Oct 2022)
2. LangChain 1.0 [Release Blog](https://blog.langchain.com/langchain-langgraph-1dot0/) (Oct 2025)
3. [Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph), by LangGraph
4. Great overviews from the LangChain docs!

- [Philosophy](https://docs.langchain.com/oss/python/langchain/philosophy)
- [Retrieval](https://docs.langchain.com/oss/python/langchain/retrieval)
- [Component Architecture](https://docs.langchain.com/oss/python/langchain/component-architecture)
- [Context Overview](https://docs.langchain.com/oss/python/concepts/context)
- [Context engineering in agents](https://docs.langchain.com/oss/python/langchain/context-engineering)
- [Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview)
- [Observability Concepts](https://docs.langchain.com/langsmith/observability-concepts)

# 🗺️ Overview

In Module 2, we introduce the Agent. What is an agent, exactly, and how do we use the construct to build awesome AI applications? And by the way, what does "agent" have to do with "RAG?"

The core **concepts** we'll cover include the big idea behind the definition of an agent that's [been agreed upon](https://simonwillison.net/2025/Sep/18/agents/) by the industry; that is, that "an LLM agent runs tools in a loop to achieve a goal." We'll take this idea further and discuss the "agent harness" as well. In addition, we'll cover a bit of the history of Langchain and its evolution to v1.0. 

The core **code** we'll cover includes the fundamentals of LangChain - the core constructs behind the framework, and when to choose one level of abstraction (e.g., [LangChain](https://docs.langchain.com/oss/python/langchain/overview)) versus another (e.g., [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview)). We'll build a simple agent and we'll also learn how to monitor our application using [LangSmith](https://docs.langchain.com/langsmith/home). From there, we'll use LangChain's [Middleware](https://docs.langchain.com/oss/python/langchain/middleware/overview) along with our choice for best vector databse ([QDrant](https://qdrant.tech/)) to build a "RAG Agent." In other words, we'll build an agent that uses a tool, and that tool will do RAG. .

# 🕴️ What is an Agent?

The term “agent” is often quite confusing. What does it mean for something to be “agentic?”

> "[**Agents**] might be neurons ... neurons [form] brains ... *At each level, new **emergent structures** [form] and engage in new emergent behaviors.*  Complexity [is] a science of **emergence**.”  ~ M. Mitchel Waldrop, [Complexity](https://www.goodreads.com/book/show/337123.Complexity)

While the level of complexity of what we consider an AI agent is bound to increase with time, you must understand a few things if you’re looking to build, ship, and share agentic applications today.

- Agent == Agentic; this is not a useful distinction to quibble about.
- Agents are a pattern, not a thing.  The Reasoning-Action pattern.
- Agents leverage tools through function calling. Most tools are aimed at improving search and retrieval.
- Better retrieval = better RAG.  Therefore, agents often leverage the RAG pattern.

Here is our current, working definition, of the word “Agent” in the context of building production LLM applications.

📖

**Agent**: A system that can leverage (or emulate) reasoning (or equivalent processes) to make dynamic decisions in an application flow

Luckily, for us, there has been some progress on this front! As of September 18, 2025, we appear to have converged

> **An LLM agent runs tools in a loop to achieve a goal. ~** [I think “agent” may finally have a widely enough agreed upon definition to be useful jargon now](https://simonwillison.net/2025/Sep/18/agents/) by Simon Willison

Though we have seen many [agent-definitions](https://simonwillison.net/tags/agent-definitions/) and we have looked at many ourselves (e.g., [What is An Agent?](https://www.youtube.com/live/PsjMHb4nl24?si=HxgUJ5AByzUnhfYR)) - and it gets quite fascinating! - these days we basically have enough of a handle on things to move forth and build 🏗️, ship 🚀, and share 🚀 some agents!

# 🤔 The Reasoning-Action (ReAct) Framework

The Reasoning Action pattern looks new, but describes logic as old as AI.

- **Reason**: If (something happens)
- **Action**: Then do (something else)

The ReAct paper was built specifically by combining two ideas:

> While large language models (LLMs) have demonstrated impressive performance across tasks in language understanding and interactive decision making, their abilities for reasoning (e.g. **chain-of-thought prompting**) and acting (e.g. **action plan generation**) have primarily been studied as separate topics.  ~ Cao, et al.

The idea is simple but wide-ranging: 

> reasoning traces help the model induce, track and update action plans as well as handle exceptions, which actions allow it to interface with and gather additional information from external sources such as knowledge bases or environments.

It’s worth reviewing the primary figure from the original paper in detail, as well as other use cases:

# 🧰 Tool Calling (i.e., Function Calling)

Note the line from the last section: “**gather additional information from external sources** such as knowledge bases or environments.”

Gathering additional information, especially information that is current, is often the job that’s left to tool calling, also known as function calling.

OpenAI was the first to release function calling in July 2023, but since then it’s gained much steam and there are even [function-calling leaderboards](https://gorilla.cs.berkeley.edu/leaderboard.html) now that rates function-calling against benchmarks.

Simply put, LLMs are *fine-tuned* for function calling.  That is, their output schema is constrained to output code capable of calling another API, or function.  This, in effect, makes connecting GPTs to external tools and APIs much easier and more reliable.

It should be noted that the beginning of function calling was simple prompting; that is, engineers telling the LLM `always output answers in JSON format`.  Over time, few-shot learning became fine-tuning, as it tends to as we move down the task-specific spectrum.  These days, we can simply set the `response_format` to `{ "type": "json_object" }` directly when using OpenAI (and other function-calling) tooling.

# 🪟 Context Engineering

It is important to understand where agents fit into Context Engineering. To do that, let’s properly visit the fundamental foundations from which the term was coined:

As Dex Horthy reminds us:

> Everything that makes agents good is context engineering ~ [12-factor Agents: Patterns of reliable LLM applications](https://www.youtube.com/watch?v=8kMaTybvDUw) by Dex Horonty

It’s worth digging into the talk that coined the term in more detail here, as it’s similar in some sense to reading the OG RAG paper. Here are the 12 (err, 13) factors:

- [Factor 1: Natural Language to Tool Calls](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-01-natural-language-to-tool-calls.md)
- [Factor 2: Own your prompts](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-02-own-your-prompts.md)
- [Factor 3: Own your context window](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md)
- [Factor 4: Tools are just structured outputs](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-04-tools-are-structured-outputs.md)
- [Factor 5: Unify execution state and business state](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-05-unify-execution-state.md)
- [Factor 6: Launch/Pause/Resume with simple APIs](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-06-launch-pause-resume.md)
- [Factor 7: Contact humans with tool calls](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-07-contact-humans-with-tools.md)
- [Factor 8: Own your control flow](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-08-own-your-control-flow.md)
- [Factor 9: Compact Errors into Context Window](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-09-compact-errors.md)
- [Factor 10: Small, Focused Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md)
- [Factor 11: Trigger from anywhere, meet users where they are](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [Factor 12: Make your agent a stateless reducer](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-12-stateless-reducer.md)

**Honorable Mentions / other advice**

- [Factor 13: Pre-fetch all the context you might need](https://github.com/humanlayer/12-factor-agents/blob/main/content/appendix-13-pre-fetch.md)

# 🔁 LangChain v1.0 - The Agent Loop

With the new release of v1.0, LangChain has [made it easier than ever for us to build agents](https://youtu.be/r5Z_gYZb4Ns?si=9qOJ_Og2_NJ9hs3W) with the Agent Loop. 

It consists of two main steps:

1. **Model call** - calls the LLM with a prompt and available tools, returns either a response or a request to execute tools
2. **Tool execution** - executes the tools that the LLM requested, returns tool results
3. Repeat

The `create_agent` construct is what we use to build agent loops. That's what we'll do in today's module!

At least, it's what we use when you use LangChain. As we'll see, when we get more complex we need to go to a heavier duty tool like LangGraph.

# 🕸️  LangGraph

The essence of LangGraph is that it uses graphs to add cycles.  

**Why Cycles?**

We can think of a cycle in our graph as a more robust and customizable loop. It allows us to keep our application ***agent-forward*** while still giving the powerful functionality of traditional loops.

Due to the inclusion of cycles over loops, we can also compose rather complex flows through our graph in a much more readable and natural fashion. Effectively allowing us to recreate application flowcharts in code in an almost 1-to-1 fashion.

**Why LangGraph?**

During this module, *we will be using LangGraph as a Directed Acyclic Graph (DAG*).  Beyond the agent-forward approach - we can easily compose and combine traditional DAG chains with powerful cyclic behavior due to the tight integration with LCEL. 

In this way, LangGraph is a natural extension to LangChain's core offerings!

## Graphs

Graphs are collections of connected objects: nodes and edges.

- **Node**: Think `function` or `runnable`; i.e. *something that changes **state***
- **Edge**: Think path to take; i.e., *where to pass **state** object next*

A state object is initially defined by passing a state definition to a class representing the graph.  This state object, or `StateGraph`, gets updated over time.  The agent's internal state is represented simply as a list of messages.  Remember how we interacted with the OpenAI API with a list of messages with roles?  Same idea.

Just as every component of a chain is a runnable, each node in our graph can be a runnable, or even an entire chain!  

Welcome to the next layer of abstraction.

## Going Deeper

Why did the LangChain team develop LangGraph?



Read more here: [Building LangGraph: Designing an Agent Runtime from first principles](https://www.blog.langchain.com/building-langgraph/)  

---

Do you have any questions about how to best prepare for Session 4 after reading? Please don't hesitate to provide direct feedback to `jacob@aimakerspace.io` or `Jacops`on Discord!
