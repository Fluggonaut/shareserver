class Stack:
    def __init__(self):
        self._stack = []

    def is_empty(self):
        if not self._stack:
            return True
        else:
            return False

    def push(self, el):
        self._stack.append(el)

    def pop(self):
        if self.is_empty():
            raise IndexError("Stack is empty.")
        return self._stack.pop()

    def top(self):
        if self.is_empty():
            raise IndexError("Stack is empty.")
        return self._stack[-1]
