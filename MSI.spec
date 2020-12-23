# PMSI spec
@ State modeling
M -> (write, active, dirty)
S -> (read, passive, clean)
I -> (invalid, passive, clean)
@ Txn specs
# Transitions from I 
(I, OwnReadM) -> S
(I, OwnReadP) -> M
(I, OtherRead) -> I
(I, OwnWriteM) -> M
(I, OwnWriteP) -> M
(I, OtherWrite) -> I
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
(M, OtherRead) -> I
(M, OwnWriteM) -> M
(M, OwnWriteP) -> M
(M, OtherWrite) -> I
