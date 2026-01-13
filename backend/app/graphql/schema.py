import strawberry
from app.graphql.queries import Query
from app.graphql.mutations.user import UserMutations
from app.graphql.mutations.task import TaskMutations
from app.graphql.mutations.integrations import IntegrationMutations

@strawberry.type
class Mutation(UserMutations, TaskMutations, IntegrationMutations):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)