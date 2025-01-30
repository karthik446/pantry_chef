# What is this

Did a bunch of stuff..There is no autocomplete in this doc, so bare with typos. It's mostly going to be you.. so yeah just read through this before changing anything, if you see typos idk just fix it, maybe? whatevr (now..now.. it's inteded)

Goal of this project:
technically:
kind want to see how effective and observable communication can i build between a bunch of ai agents and a standard GO API. If i get the f/w right once, i can have n number of agents and n number of apis.. minority report!!! We are using everything open source!! except new-relic, note on that somewhere.

in reality:
user has set of pantry items, when a search happens it shows recipes (included source url), and pantry_match. Hence the name pantry_chef.

# As Of Jan 25

Speaking of lazy, I've realied heavily on AI to build this, i mean considering this is currently a greenfield and the password is postgres (as of writing this), so yeah.. tread lightly. Although the current cluster has been torn down and rebuild multiple times, at this point there aren't a lot of tests in neither agent or api. There is some documentation but it's AI written and not proof read.

## Alright what did I do?

### Agents

- We have a simple recipe_agent that uses smoleagent default opensource free agent.
  - All it does is takes in a search string
  - Queries API to see if this search was seen before, if so returns urls
  - Uses DuckDuckGo Tool to make the search, excluding above urls domains.
  - Tries to Scrape the Recipe (using coded scraping for now)
  - If it can find all the details submits the recipe to the API (db)

### API

- GO API that has CRUD for recipes, ingredients
- Custom JWT Auth ✅
- Refresh Token functionality ✅
- Migrations and Seed ✅
- Custom AUTH Middlewares ✅

### Deployment

- [k8s Overview](k8s.md)
- [k8s implementation](k8s-implementation.md)
