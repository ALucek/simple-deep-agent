# DESIGN.md

## Initial philosophy and planning

**Immediate thoughts**: Deep research is a classic example of an Agent use case, its one of the first "agentic" capabilities introduced to chat assistants post general single function/tool calling abilities like web search (RIP the bing web search API and the arms race of coupling search with specific model providers through vertex and azure). The point of deep research is to trade latency and cost for accuracy, favoring a wider and broader fan out style search to try and capture as much relevant context about the requested topic, synthesize key insights, and return back in the desired style and structure to the user. As such, our approach should not disregard latency (or cost!), but users of deep research systems tend to expect this tradeoff up front. 

The report style and topic was left general, so our agent must broadly support general queries and open requests (i.e. structure, format, other desired personalizations to the output that a user may request in the prompt). This doesn't _complicate_ things per se, but it would make evaluating performance downstream a little more difficult. It's easier to say, verify a deep research system that is meant to follow a strict format and information gathering style/defined aspects (E.g. a system that would take in a list of companies, perform comprehensive research, and output the same briefing for each). Keeping our deep research agent's focus and support broad adds some subjectivity and widens possible expectations from users. Not an issue but would want to keep an eye on output feedback as defining quality and accuracy to a broad use case will depend on usage trends that I will not be able to capture immediately here.

Deep research agents within chat experiences these days also tend to be seperate processes, in other words the interaction and request in the chat kicks off a seperate deep research "job" that executes and you can continue the chat conversation while that is in progress. The purpose of this is to create the deep research agent part of this, thus I will make the assumption that this will operate as the report generation engine, rather than chat assistant. We can table then more chat assistant focused features like explicit interaction memory and prompting quirks/context injection for encouraging helpful behavior in an applied domain that would be expected for chat, but aren't immediately necessary for report generation. 

The purpose of this is then also to keep things "simple". As such, I'll table features unrelated to designing and implementing the core report generation engine, such as deployment/infra, frontend/UX, persistent storage, etc. 

With this I can explicitly outline some larger out of scope features that could be cool to explore either in the future or as part of a complete system.

Out of scope
- Optimizing chat assistant related behavior
- Memory management/system
- Deployment specifics (thread handling, double text strategies, etc.)
- Frontend/user experience
- Creating a framework/factory (e.g. deepagents)
- Code execution/sandbox or related orchestration

Now taking a couple steps back and pondering the idea a little, **deep agents** have some generally agreed upon capabilities and an architecture that's been popularized by coding agents like cursor, codex, claude code, etc. We can expect to see a primary orchestrator model that has a detailed and thurough system prompt, access to a filesystem + relevant (shell-based) navigation/editing tools, a no-op todo list tool to keep the model on track, and the ability to delegate to specialized sub agents in seperate context windows. For simplicity's sake, we'll forgo the filesystem implementation, but I would like to keep the orchestrator and task delegation sub agent setup. We'll assess the necessity of a todo list as I develop, models these days are generally good at multistep actions/parallel tool calling which I can take advantage of, likely with some explicit instructions in the prompt. Report generation from web search results is relatively straightforward when compared to something like a complex system implementation that requires multiple seperate actions and steps.

Also it would be a cop out to use deep agent abstractions, like the `deepagents` package for the sake of this exercise.

Other similarly inspired setups also approach context and sub agent execution via sandboxed code execution, both for this and for handling responses that may overflow the context window. I don't anticipate needing this level of sophistication, and if I implement our sub agent delegation effectively and web result handling I shouldn't run into many token limitations. Also this complicates things greatly! We'll add it into the out of scope for this exercise list.

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
- Domain specificity: As this is meant to support a broad range of topics, I won't limit to categories like `people` or `news` or certain domains. Could be interesting to note this as a configuration addition
- Text length: Exa's API has the ability to return full text, summary, or highlights from searched links. Will need to balance token consumption with text/context length and need (or not) for exact page results
- Relevance: We will get back a similarity score with results, I could apply an additional filter for some relevance threshold on top of the already deemend relevant and returned back objects
- Date Range: Should I limit to a specific range to prevent out of date/stale web content from being interpretted? Likely not as this is a general research agent, could include as configurable
- Cost: The models will be running a nontrivial amount of web searches, which even if priced at a fraction of a cent per can add up. Have seen the cost of licensing web search credits surpass that of LLM input/output token consumption for deep research tasks, so this should be considered.

Well, I learned today that Exa's pricing model claims of $5/1k for up to 1-25 results does not include page content or highlights, which is billed at $1.00/k. Some quick math, 1000 searches with 25 results each could come out to a total of $30. Since that's a bit ridiculous right now, we'll consider the other two providers that include content as part of their feature set and total cost: perplexity & tavily. I'll be implementing with Tavily since it has the option to return back full page contents, whereas perplexity's only returns back summary/highlights. Tavily supports both options, and I may want to implement a feature like generating citation links with text fragments (OpenAI's deep research does this) so having the option to return raw content is a nice to have. Tavily also has some cost/depth tradeoffs with their 'advanced' search but I can use some of their API tricks to automatically determine what depth is required, specifically with `auto_parameters` which will determine both topic and search depth based on the query automatically. Optionally, I could override this with a configured preference in the future. 

We'll stick to text content processing for this. Ran some queries to see if the returned images would be relevant, they mostly werent for more niche topics. If I want to, say, research paris then itll grab great general pics, but this quality degrades as the content becomes more niche. We can add image handling as a future enhancement

We'll also shift our approach to avoid the raw content. A quick check of how many tokens one web search with 5 queries returning back gave us 108k tokens (compared to 358 for just the extracted relevant content section). Could be interesting to have a future deep dive into the raw contents ability with a crawl endpoint or similar.

As a note, one of our goals is to limit the amount of times a piece of retrieved content is processed, i.e. reingested or restated by an LLM. I've found that constantly reviewing or summarizing can flatten the actual useful information/exacts that I want to be grounded in the retrieved context. This will additionally help us with implementing inline text fragment links.

### Graphs

Our agent graphs are going to be relatively straightforward. We will start with the user input, this input will be passed to a node that invokes an LLM to ask some clarifying questions (human in the loop style interrupt), the user will type in a response and the graph should either resume from that checkpoint with the additional message inserted, or the clarifying LLM should be able to determine when to kick off the deep research sub graph. The deep research sub graph will follow a standard ReACT setup and have the ability to invoke multiple research agents. In considering the method of invocation, I will rely on tool calling here rather than something like `Send()` to allow a more loose flow. `Send()` would be useful if I wanted a more linear graph but I want to rely on the intelligence of the model to determine if it has adequate information or not. We can also be a little more specific than implementations like deepagents take with the `task` tool as I only have one expected sub agent type. This sub agent will then have the web search tool available to perform said research. It will perform some number of web searches, create an intermediate cited report as a response, and return this back to the orchestrating LLM. 

We also want to make sure I can do everything efficiently, in parallel!

## Findings from the Future

Following the philosophy and general outline of thinking here, I proceeded to iterate and implement.

The web search tool was defined first, and evolved a few times over the course of development. Some of the major considerations and findings were:
- (summarized from above) Exa was cost prohibitive, switched to Tavily to still get raw content at a cheaper price (Perplexity search API doesn't return consistent verbatim contents, would break linking to specific text fragments)
- the built in tool node supports concurrency, when trying to define my own tool node to limit the amount of web search calls per run I discovered this as my search results were sequential. 
    - Switched everything over to async
- The built in Tavily Search integration inherits from BaseTool, which I wrapped in a structured tool, which made it kinda messy and redundant, this was mostly to try and implement a global rate limiter
    - Rate limiting ended up being a bit of a mess, instead relying on vertically scaling my API to the 1000 req/min tier, and downstream implementing a 25 max calls per run limit.
- Implemented a relevancy score filter, this ends up being useful in situations of limited web results (e.g. if I hit tavily with "Adam Lucek" theres only a few really relevant results, the rest can be filtered out). 
- Gave some consideration to tool instantiation, my original had a search tool every search invocation, considered some optimizations like LRU cache
    - eventually ended up instantiating the tool within each node later on. Gains of optimizing this with something like a global tool not worth the headache rn, especially for a high "latency" system thats going to take 5 mins anyway
- For simplicity's sake, hardcoded values. Future improvements could be made with making this configurable and tuning the various parameters
- To keep things simple, it will only take in a query without any additional model-defined parameters
    - Worth exploring exposing some additional KWARGs for the LLM to pop into a search query like date filtering, topic filtering, etc.

I then proceeded to build the core graph to build on deciding on a few specific choices:
1. I will implement the clarification step as an LLM call and an interrupt node
2. I will have a main orchestrator node that handles the delegation and creation of the final report
3. I will have a sub graph that is invoked via a function call from the orchestration node

- I created two states, one for the main orchestrator and one for the research agent, these explicitly define a messages field with an `add_messages` reducer 
    - This was mostly to support the requirement from the spec, could be simplified with a `MessagesState` but better safe than sorry
- I considered what additional fields would be needed
    - Personally, I think an elegant implementation of agent context handling involves relying on a straightforward historical list of messages, opposed to handling extra variables in state values and injecting them at different points. Obviously, this is mostly for context handling and not true all the time, but wanted to keep things consistent for this implementation. There are plenty reasons you'd want to keep additional info in state, such as to hold a count of web searches for limiting, which I ended up doing with my research sub graph, or other processing logic
- Also, decided may as well implement config handling for the models as it wasn't much overhead to inject, added values to specify model and temperature for the three various LLM 'roles' you'll interact with.
    - For the sake of time and complexity, kept config low, plenty opportunity as mentioned in the web search tool to add more configurations, split them out into seperate ones, etc for both the models, interactions, so on, so forth.
- I decided to use structured outputs with defined models to ensure consistency and reliability, as tends to be standard.
    - Defined via pydantic so we can use all the other features of the package if needed
- Model instantiation is using OpenAI as this is the provided API key, future considerations for additional model provider support

As for the nodes and edges, these followed much of the outlined philosophy. We initiate the main graph which immediately goes to a clarification node with the user's input. 
- We instantiate a model with the clarification system prompt and state message history
    - We allow the full message history as multiple clarifications may be necessary
- This hits a conditional edge where if the model has determined that we need clarification, we return the question and hit an `interrupt`. This conveniently checkpoints and pauses our graph while we insert a new value, which ends up being added to the message history along with the AI's clarifying question
    - `interrupt` is nice here as it handles all checkpointing and resuming so we don't have to deal with threads, ids, and resuming checkpoints manually. 
- This is returned back to the clarifying node where the model can run it back with more questions, or pass to the orchestrator by returning `None` in the question

To fully implement the the orchestrator we need the research sub agent graph defined and invokable as a tool.

The initial implementation of this was a simple research agent node and ToolNode with web search. As we got into testing, this needed to be evolved for a few reasons:
- In one of the original naive implementations, the model literally spent like 5 minutes generating what appears to be over 100 parallel web searches for some ridiculous reason https://smith.langchain.com/public/60f3bcaf-b3d6-4f53-84af-1f76d5c5df8e/r
    - So obviously we were not going let that just happen, thus had to redesign a custom web_search_node to handle our web tool invocations 
    - Also if Tavily literally doesn't find any results it returns a string rather than a dict, so had to handle that https://smith.langchain.com/public/ed69fcd7-0d85-4c47-9692-fb3cb632ada3/r
    - This did break the parallelization that the ToolNode has built in, so had to switch to async handling. While we were here went ahead and converted everything for posterities sake in the nodes as we want the research agents to be able to be ran in parallel anyway and we can get some efficiency gains/reduce latency
    - This allows allows us to implement the max limit logic, where we check our config and return a warning toolmessage instead of executing additional tool calls
- But with these kinks ironed out, the rest is straightforward agent -> web search -> execute -> return -> more or generate and end

With our sub graph defined, we needed a way to package it into a callable tool
- This was a lot easier to handle as we just pop the graph in a function with a query (the generated instructions from the orchestrator calling the tool) passed as a human message, which we further bundle as a StructuredTool from a function.

This can be connected to the orchestrator within a ToolNode nicely, so we do that and then conditional between it and end.

With the initial stage out the prompting came next, one for each role of the LLM
- The clarifier simply has instructions to take in the query and generate 2-3 followup questions (although it likes to ere on the side of 3 always).
    - I originally said 5, but thats a horrible user experience to answer 5 long questions
    - Also had to stop it from asking about depth/format as this would be covered in the orchestrator prompting
- As always we provide instructions on what to return along with an outline example.
- The research agent has a more interesting prompt and required a few explicit instructions
    - Search query guidelines since it kept running search engine filter queries like "site:reddit.com" etc when it should be natural language
    - Avoid multiple topics in a single query, split them into individual runs
    - Don't use the search tool 200 times please (although this is enforced its nice to be explicit)
    - Then two good behavioral examples and a bad example.
    - **Importantly**, we also take this time to implement text fragment URL linking with sources. This will allow all claims and sources to link directly to and highlight the text on the page when clicked through. I've found users love this function as they would rather not find the exact citation themselves, and for large/non text content it can be difficult to find where insights are pulled from if not direcly noted.
    - We reinforce this behavior with explicit rules
    - For verbosity and completeness, we request minimum 5 paragraphs of 20 sentences. Needed to specify exacts as the models err on the side of less if not
- The orchestrator prompt is the main "program" of the agent, so a little more goes in with:
    - instructions on how to call the research agent, mostly around parallel tool calling and not asking a research agent to do multiple topics at once
    - behavior examples to encourage specific flow, examples of good behavior and bad behavior outlined
    - The same citation instructions as the sub agent to propogate those links through
    - Report format, which encourages the style and verbosity of the report. These instructions are mostly focused around styling a report similar to those returned by ChatGPT tool.
        - The format took a while to tune, the model tended to make very short and choppy lists unless explicitly prompted with sentence requirements. Also noticed PDFs don't equally handle text fragment based citations so instructions.
- Across all of these also added date/time so they don't keep thinking theyre in 2024
- One bug that came up was the markdown formatting breaking, this was identified as the ~ character being used for approximation, which caused strikethroughs to render and break text fragment linking, prompt was updated to reflect 

This got us closer to an ideal behavior, but the system still suffered from not going too deep, the orchestrator would kick off a couple sub agents then generate a report. So decided to also implement the todo list tool to the orchestrator
- As we understand these days, the todo list tool isn't meant to actually do anything but rather keep the model consistently reflecting on some workflow that it defines. 
- This implementation is very similar to other implementations in that we offer a list of todos that the model creates with a description and status, and instructions in the prompt were added to encourage frequent usage and show examples.
    - We implement this as a seperate tool node on the graph for a few key reasons
    - We want to encourage the model choosing either the sub agents OR interacting with the todos explicitly. This is intended so that we have an isolated planning stage that the llm works through before taking an action/subsequent action
    - We don't want parallel todo list calls as it would be either redundant or unnecessary. The intended flow is to plan, act, observe, then update the plan (todo list)
    - But seeing as this is a noop tool the implementation is relatively straightforward in code, further defined through the prompt. Further optimization could happen by explicitly restricting to 1 call and returning some error message

And with all these various iterations and findings, we land on a working deep agent implementation, you can see an example here:

Initial message and first interrupt: https://smith.langchain.com/public/00194993-eb6f-4012-8e64-58924578594d/r
Second interrupt: https://smith.langchain.com/public/c4eed224-e071-4c5c-91dc-0295bf016aa8/r
Main Report Generation: https://smith.langchain.com/public/c11641ff-0516-4f8b-b161-2066b70a9734/r

Which produced [the report here](/examples/report.md)

## thoughts/future/optimizations

model choice - I default to OpenAI's models due to the provided resources, using gpt 5.2 as our all around model. OpenAI's tone and voice is relatively lacking, would likely use an Anthropic model like Opus for a more lively report read. 5.2 also has some quirks on tool calling, tends to try and compact actions and minimize tool calling, unlike gpt 5 which loves to fire off a tool. Some considerations of models with a higher tendency for tool calling in the tool calling heavy roles like the orchestrator, then those with less tendency for the sub agents, where we can somewhat take advantage of conservative tool calling to limit expensive actions like web search.

Supervisor, revisor, etc - As mentioned earlier, I've found that adding additional reviews and transformations of the text across llms tends to flatten the information. The use of sub agents for context management is a great trick to distill and then synthesize with a supervisor keeps text closer to the user. 

Some future direction ideas to try
- Finding similar queries/reports and displaying to not duplicate work (i.e. some memory system)
- filesystem integration
- Different web search provider(s)
- image handling, both understanding and placing in line with report
- Text fragments for PDF file types 
- Tools decoupled as MCP
- Tools decoupled as Skills
- Configurable web search parameters
- configurable web search providers
- More configuration in general for all knobs
- support for other llm providers
- Implement functionalities using middleware framework
- OpenAI's new editable todo list kickoff rather than an LLM clarifier
- Whether additional reviewer steps are worth it

Some known optimizations to the current implementation:
- handle invalid tool mixes, i.e. if the tool call is a todo list AND sub agents.
    - warning message returned via a tool message from a new node
- retry policy
    - Add to LLM models and nodes if noticing failures
- global rate limiting for web search
    - create an async rate limiter, attach to the tool (would need to be more custom than my initial try)
- Limit clarifications explicitly (often asks twice)
    - either via prompting, or pass the interrupt to the orchestrator directly
- tune relevancy score
    - Assess if search results are getting cut off that ARE relevant and tune
- Link format checking and consistency
    - extract and match against patterns to ensure formatting is right
- text fragments on reactive pages
    - I fear this may be a per page and how it handles highlighting issue
- Explicit handling of tildes that break markdown formatting 
    - run a check and replace for out place tildes

## Evals

When making a quick dataset to try some evals out, were able to perform some error analysis. Two quick bug fixes came out from this, namely:
- Section titles being numbered (looked bad)
- Some verbosity issues and formatting (i.e. not long enough)
- markdown breaking with strikethroughs via the tilde, more pressing

Pushed prompt updates for these, but also worthwhile adding in some explicit evaluators for these. For the sake of time we won't do a full eval implementation, but these would be useful:
- Function for assessing stray tildes outside of text fragments
- Function for checking for list numbers in headers
- Structure adherence - LLM as a Judge
- Verbosity - Either length or LLM as a Judge
- Link fromatting consistency - Funtion to match markdown format
- Check links for 200/404, sometimes models mess up characters in links due their complicated strings. Could extract and explicitly check to make sure the model is accurate.
- search tool object count - if we continue to see small searches maybe our threshold of relevance is too strict
- Pairwise for testing various model(s) and their performance
...
- User preferences, further quirks surfaced as we observe behavior

I have a larger philosophy on evaluations that I've written up here: https://lucek.ai/blogs/llm-evaluations

---

Thanks for reading my design brain dump!