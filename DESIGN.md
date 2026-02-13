# DESIGN.md

So the goal is to create a deep research implementation for report generation grounded in web search. My language of choice for this will be **python**

Theres a couple criterium upon which this agent will be judged, from the spec we see:
- Code quality
- Report structure & generation quality
- Communication of ideas (_"talk through any questions or ideas you have for performance improvements"_)
    - Assumption that this will be covered partially by the design document, and partially by any live discussion/walkthrough

There are some explicitly defined requirements as well, some pertaining to the overall task some to the agent:
- It should have a `messages` field in state
    - This will handle both the user messages and assistant messages, with the final answer being returned as an assistant message (as opposed to the report being stored in a seperate field in the state, filesystem, store, etc etc)
    - Can optionally include other relevant internally generated messages, either directly in the messages field or seperate fields
- Users should be able to pass in a query and be returned back a report grounded in context from the web
- It should use web search APIs to gather context for the report
    - with some recs around tavily (now part of nebius!), exa, or SerpAPI
- This `DESIGN.md` doc that outlines my thought process in designing the agent.
    - This should operate as a brain dump, some ideas of what to include are what did i try with successes/failures, how these successes/failures influenced changes
    - Acknowledgement of shortcomings/time limitations, outlined fixes if not under time pressure.
    - Future features and improvements/optimizations
    - Any other ways you want to use 
- public Github repository containing the code
- `README.md` with instructions on setup and run locally
- Optionally setup with LangSmith studio, and screenshot of the graph from LangSmith Studio

There are also some stretch goals:
- Configuration support (model, search provider, number of searches, system prompt, report structure, etc...)
- Evals!

**Immediate thoughts**: Deep research is a classic example of an Agent use case, its one of the first "agentic" capabilities introduced to chat assistants post general single function/tool calling abilities like web search (RIP the bing web search API and the arms race of coupling search with specific model providers through vertex and azure). The point of deep research is to trade latency and cost for accuracy, favoring a wider and broader fan out style search to try and capture as much relevant context about the requested topic, synthesize key insights, and return back in the desired style and structure to the user. As such, our approach should not disregard latency (or cost!), but users of deep research systems tend to expect this tradeoff up front. 

The report style and topic was left general, so our agent must broadly support general queries and open requests (i.e. structure, format, other desired personalizations to the output that a user may request in the prompt). This doesn't _complicate_ things per se, but it would make evaluating performance downstream a little more difficult. It's easier to say, verify a deep research system that is meant to follow a strict format and information gathering style/defined aspects (E.g. a system that would take in a list of companies, perform comprehensive research, and output the same briefing for each). Keeping our deep research agent's focus and support broad adds some subjectivity and widens possible expectations from users. Not an issue but would want to keep an eye on output feedback as defining quality and accuracy to a broad use case will depend on usage trends that we will not be able to capture immediately here.

Deep research agents within chat experiences these days also tend to be seperate processes, in other words the interaction and request in the chat kicks off a seperate deep research "job" that executes and you can continue the chat conversation while that is in progress. The purpose of this assessment is to create the deep research agent part of this, thus we will make the assumption that this will operate as the report generation engine, rather than chat assistant. We can table then more chat assistant focused features like explicit interaction memory and prompting quirks/context injection for encouraging helpful behavior in an applied domain that would be expected for chat, but aren't immediately necessary for report generation. 

The purpose of this is then also to keep things "simple". As such, I'll table features unrelated to designing and implementing the core report generation engine, such as deployment/infra, frontend/UX, persistent storage, etc. 

With this we can explicitly outline some out of scope features that could be cool to explore either in the future or as part of a complete system.

Out of scope
- Optimizing chat assistant related behavior
- Memory management/system
- Deployment specifics (thread handling, double text strategies, etc.)
- Frontend/user experience
- Creating a framework/factory (e.g. deepagents)
- Code execution/sandbox or related orchestration

Now taking a couple steps back and pondering the idea a little, **deep agents** have some generally agreed upon capabilities and an architecture that's been popularized by coding agents like cursor, codex, claude code, etc. We can expect to see a primary orchestrator model that has a detailed and thurough system prompt, access to a filesystem + relevant (shell-based) navigation/editing tools, a no-op todo list tool to keep the model on track, and the ability to delegate to specialized sub agents in seperate context windows. For simplicity's sake, we'll forgo the filesystem implementation, but I would like to keep the orchestrator and task delegation sub agent setup. We'll assess the necessity of a todo list as we develop, models these days are generally good at multistep actions/parallel tool calling which we can take advantage of, likely with some explicit instructions in the prompt. Report generation from web search results is relatively straightforward when compared to something like a complex system implementation that requires multiple seperate actions and steps.

Also it would be a cop out to use deep agent abstractions, like the `deepagents` package for the sake of this exercise.

Other similarly inspired setups also approach context and sub agent execution via sandboxed code execution, both for this and for handling responses that may overflow the context window. I don't anticipate needing this level of sophistication, and if we implement our sub agent delegation effectively and web result handling we shouldn't run into many token limitations. Also this complicates things greatly! We'll add it into the out of scope for this exercise list.

With much of this coming together, there's one extra capability consideration- query clarification. Or, in other words, the step that has an LLM ask a few clarifying questions before the report is actually ran. I appreciate this step as it forces the user to get more narrow and specific rather than throwing vague and broad prompts into the engine. We'll include this as something to test in scope.

So, we'll need to define some things:
1. Web search tool
2. Sub Agent tool
3. Main orchestration graph
4. Sub agent graph
5. (to be tested) todo list tool
6. (to be tested) Clarifying question LLM

### Web Search Tool

Starting with the web search tool, I've used a mix of the Perplexity search API and Tavily extensively, so I'll implement a web search tool with Exa to switch things up and learn something new, plus they've been boasting their usage as somewhat 'LLM optimized' so let's see. Few considerations:
- Max results: We'll likely be encouraging the research sub agents to execute multiple (e.g. 5 or so) web search tool calls 
- Domain specificity: As this is meant to support a broad range of topics, we won't limit to categories like `people` or `news` or certain domains. Could be interesting to note this as a configuration addition
- Text length: Exa's API has the ability to return full text, summary, or highlights from searched links. Will need to balance token consumption with text/context length and need (or not) for exact page results
- Relevance: We will get back a similarity score with results, we could apply an additional filter for some relevance threshold on top of the already deemend relevant and returned back objects
- Date Range: Should we limit to a specific range to prevent out of date/stale web content from being interpretted? Likely not as this is a general research agent, could include as configurable
- Cost: The models will be running a nontrivial amount of web searches, which even if priced at a fraction of a cent per can add up. Have seen the cost of licensing web search credits surpass that of LLM input/output token consumption for deep research tasks, so this should be considered.

Well, I learned today that Exa's pricing model claims of $5/1k for up to 1-25 results does not include page content or highlights, which is billed at $1.00/k. Some quick math, 1000 searches with 25 results each could come out to a total of $30. Since that's a bit ridiculous right now, we'll consider the other two providers that include content as part of their feature set and total cost: perplexity & tavily. I'll be implementing with Tavily since it has the option to return back full page contents, whereas perplexity's only returns back summary/highlights. Tavily supports both options, and we may want to implement a feature like generating citation links with text fragments (OpenAI's deep research does this) so having the option to return raw content is a nice to have. Tavily also has some cost/depth tradeoffs with their 'advanced' search but we can use some of their API tricks to automatically determine what depth is required, specifically with `auto_parameters` which will determine both topic and search depth based on the query automatically. Optionally, we could override this with a configured preference in the future. 

We'll stick to text content processing for this. Ran some queries to see if the returned images would be relevant, they mostly werent for more niche topics. If we want to, say, research paris then itll grab great general pics, but this quality degrades as the content becomes more niche. We can add image handling as a future enhancement

We'll also shift our approach to avoid the raw content. A quick check of how many tokens one web search with 5 queries returning back gave us 108k tokens (compared to 358 for just the extracted relevant content section). Could be interesting to have a future deep dive into the raw contents ability with a crawl endpoint or similar.

As a note, one of our goals is to limit the amount of times a piece of retrieved content is processed, i.e. reingested or restated by an LLM. I've found that constantly reviewing or summarizing can flatten the actual useful information/exacts that we want to be grounded in the retrieved context. This will additionally help us with implementing inline text fragment links.

## Graphs

Our agent graphs are going to be relatively straightforward. We will start with the user input, this input will be passed to a node that invokes an LLM to ask some clarifying questions (human in the loop style interrupt), the user will type in a response and the graph should either resume from that checkpoint with the additional message inserted, or the clarifying LLM should be able to determine when to kick off the deep research sub graph. The deep research sub graph will follow a standard ReACT setup and have the ability to invoke multiple research agents. In considering the method of invocation, we will rely on tool calling here rather than something like `Send()` to allow a more loose flow. `Send()` would be useful if we wanted a more linear graph but we want to rely on the intelligence of the model to determine if it has adequate information or not. We can also be a little more specific than implementations like deepagents take with the `task` tool as we only have one expected sub agent type. This sub agent will then have the web search tool available to perform said research. It will perform some number of web searches, create an intermediate cited report as a response, and return this back to the orchestrating LLM. 

We also want to make sure we can do everything efficiently, in parallel!

Clarification rounds?

discuss interrupt

discuss graph and models
structured outputs
config

For tool models, why include less fields than more specifics

if tavily doesnt find results, it returns a string... good to know https://smith.langchain.com/public/ed69fcd7-0d85-4c47-9692-fb3cb632ada3/r

running ntoes
- async

Approach:
- Messages field in state, we'll explicitly define this rather than use the built in `MessagesState`

Future ideas
- Finding similar queries/reports and displaying to not duplicate
- filesystem integration
- Different web search provider
- direct text link highlighting (text fragments)
- image handling

web search, full text vs highlights

other considerations, mcp skills etc
config: web search category, web search basic vs advanced, web search date range/filter, 

evals (links return 200, 404 checks)

configurables

trade offs
- LRU cache, overkill

- switch to using @tool, easier than defining a structured tool
- had to wrap function in tool to respect the rate limiter