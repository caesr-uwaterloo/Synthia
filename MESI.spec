# PMESI spec
@ State modeling
M -> (write, active, dirty)
E -> (exclusiveRead, active, dirty)
S -> (read, passive, clean)
I -> (invalid, passive, clean)
@ Txn specs
# Transitions from I 
(I, OwnReadM) -> E
(I, OwnReadP) -> S
(I, OtherRead) -> I
(I, OwnWriteM) -> M
(I, OwnWriteP) -> M
(I, OtherWrite) -> I
# Transitions from E 
(E, OwnReadM) -> E
(E, OwnReadP) -> E
(E, OtherRead) -> S
(E, OwnWriteM) -> M
(E, OwnWriteP) -> M
(E, OtherWrite) -> I
# Transitions from S 
(S, OwnReadM) -> S
(S, OwnReadP) -> S
(S, OtherRead) -> S
(S, OwnWriteM) -> M
(S, OwnWriteP) -> M
(S, OtherWrite) -> I
# Transitions from M 
(M, OwnReadM) -> M
(M, OwnReadP) -> M
(M, OtherRead) -> S
(M, OwnWriteM) -> M
(M, OwnWriteP) -> M
(M, OtherWrite) -> I
