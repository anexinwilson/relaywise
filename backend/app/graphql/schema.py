import strawberry
from app.graphql.queries import Query
from app.graphql.mutations.user import UserMutations
from app.graphql.mutations.task import TaskMutations


@strawberry.type
class Mutation(UserMutations, TaskMutations):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)