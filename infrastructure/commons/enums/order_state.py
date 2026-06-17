from enum import IntEnum


class OrderStateEnum(IntEnum):
    PendingReview = 1
    InProgress = 2
    Complete = 3
