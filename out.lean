
#eval  (λ x ↦ x) 1
#check (λ x ↦ x) 2
#check (λ x ↦ x)


-- Peano Numbers
inductive nat where
  | zero
  | succ (n: nat)


def add (n m: nat) : nat := match n with
  | .zero => m
  | .succ n' => nat.succ (add n' m)


theorem add_comm: ∀ (n m : nat), add n m = add m n := by
  intros n; induction n
  case zero =>
    intros m; induction m; 
    case zero => simp only [add]; 
    case succ m' ih => simp only [add, ←ih]; 
  case succ n ih =>
    intros m; induction m
    case zero => simp only [add, ih]
    case succ m' ih' => simp [add,ih,←ih']


