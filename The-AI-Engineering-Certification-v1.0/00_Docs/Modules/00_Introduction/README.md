# 🧑‍💻 What is AI Engineering?

AI Engineering refers to the industry-relevant skills that data science and engineering teams need to successfully **build, deploy, operate, and improve Large Language Model (LLM) applications in production environments.**

In 2026, AI Engineers are responsible for building agents.

At AI Makerspace, we are focused on delivering only the most practical AI education. We believe that today, to be an AI Engineer (or Forward Deployed Engineer, Product Engineer, or whatever you'd like to call it), you must understand how to prototype _and productionize_.

During the *prototyping* phase, we want to have the skills to prototype with RAG and Agents:

RAG
1. Build RAG Applications 
2. Build and Implement Evals for RAG Applications 
3. Improve Retrieval Pipelines 
4. Implement multi-modal RAG pipelines

Agents
1. Build Agent Applications using leading frameworks 
2. Implement Agent Memory 
3. Build Multi-Agent Applications 
4. Monitor, Observe, and Debug Agent Applications 
5. Build and Implement Evals for Agent Applications
6. Build MCP Servers 
7. Write Agent Skills

When *productionizing*, we want to make sure we have the skills to:

1. Implement fine-tuning on leading LLMs 
2. Fine-tune leading LLMs using RL with Verifiable Rewards
3. Deploy End-to-End LLM and Agent Applications to Users 
4. Build Agents with Scalable, Production-Grade Components 
5. Deploy Production Agent Servers 
6. Deploy Production LLM Servers 
7. Build Guardrails for LLM Applications 
8. Optimize LLM Applications for Production Operation

If you haven't yet taken the initial self-assessment for v1.0, please [complete it now](https://forms.gle/62iuJMRuDP694mFo7)!

# 🌀 Design Patterns of AI Engineering

There are four patterns we’ll see time after time as we build, ship, and share throughout this course. The patterns will occur at different levels of abstraction and will work together to help us create more powerful and useful production-grade LLM applications.

The three patterns are:

- 💬 Prompt Engineering = Putting instructions *in the context window* =  `In-Context Learning`
- 🗂️ RAG = Giving the LLM ***access** to **new knowledge* = `Dense Vector Retrieval + In-Context Learning`
- 🕴️ Agents = Enhanced Search & Retrieval (e.g., Agentic RAG) = Giving the LLM access to tools = The [Reasoning-Action (ReAct)](https://arxiv.org/abs/2210.03629) pattern
- ⚖️ Fine-Tuning = Teaching the LLM *how to **act* = Modifying LLM behavior through weight updates

* as of Spring, 2026, we can add another detail to Agents; that is [model + harness = agent](https://x.com/willccbb/status/2049844685095715289)

Typically, we apply these patterns in this order when prototyping LLM applications. That is, we typically first work to optimize what we're prompting, then what we're retrieving and how we retrieve it. Agents come next, and determining the right amount and type of agents is more art than science. Once we figure out how to scale our app in production, we often return to our good friend fine-tuning, and our old friends, open-source models.

In the end, it's all about optimizing what we put in context at any given conversation turn or within any user session. In short, you might say it's all Context Engineering.

# 🔵 Context Engineering, Harness Engineering, Agent Scaffolding, and more...

From the outset, it’s important to address the elephants in the AI Engineering room.

Context Engineering was originally coined by [Dexter Horthy](https://x.com/dexhorthy/status/1940895400065749412). Of course, it's just as apt today to talk [harness engineering](https://x.com/dexhorthy/status/1985699548153467120). Further, we need to be able to identify the subtle differences between the [model, the harness, and the scaffold](https://huggingface.co/blog/agent-glossary). 

In this course, we’ll investigate from first principles what we know to be true today about the foundational elements of agentic systems, knowing that the ground will keep shifting under our feet. As Hugging Face reminds us: 

> When a field evolves quickly, its vocabulary often evolves faster than its shared understanding. Terms start to blur, get reused in different contexts, or become shorthand for ideas that are never fully explained. We are currently seeing this happen in the field of AI Agents, where concepts are getting mixed together, some are renamed, and others are widely used for a few months before quietly disappearing.

# 🎸 Vibe Checking, Evals, and the Agentic Road Ahead

Every time we build an application, we need to evaluate the application.  We need to test it, as a user would!

The pattern is simple: build, evaluate, iterate.

Vibe checking is a simple form of evaluation, and allows us to critique what we've build quantitatively. When we get more systematic, most consider that at that point we're in a more proper "evals" space.

Then come agents. While RAG evaluation is well-established in the market, agents are only now seeing more robust evaluations start to be developed. The interesting thing that appears to be happening is that _when we get better at evaluating agents, we get better at training parts of the agent harness into our new models_. This "coupling of model training and harness design" has been discussed by leaders like [LangChain](https://www.langchain.com/blog/the-anatomy-of-an-agent-harness#the-future-of-harnesses) and [Anthropic](https://www.anthropic.com/engineering/harness-design-long-running-apps) and more broadly with foundational work like [The Bitter Lesson](http://www.incompleteideas.net/IncIdeas/BitterLesson.html).

Welcome to The AI Engineer Certification, where will we explore this agentic of of LLMs as it stands in the summer of 2026.

See you in class!

Cheers,

Dr. Greg Loughnane, Ph.D
Owner & CEO, AI Makerspace
