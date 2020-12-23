# PMESI spec
@ State modeling
M -> (write, active, dirty)
E -> (exclusiveRead, active, dirty)
S -> (read, passive, clean)
I -> (invalid, passive, clean)
O -> (read, active, dirty)
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
(M, OtherRead) -> O
(M, OwnWriteM) -> M
(M, OwnWriteP) -> M
(M, OtherWrite) -> I
# Transitions from O
(O, OwnReadM) -> O
(O, OwnReadP) -> O
(O, OtherRead) -> O
(O, OwnWriteM) -> M
(O, OwnWriteP) -> M
(O, OtherWrite) -> I
