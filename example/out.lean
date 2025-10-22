
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


-- This is the add_comm from the standard library, not ours!
#check Nat.add_comm

theorem add_comm: ∀ (n m : nat), add n m = add m n := by
  intros n; induction n
  case zero => -- {{{
    intros m; induction m;
    case zero => simp only [add];
    case succ m' ih => simp only [add, ←ih]; -- }}}
  case succ n ih => -- >>>
    intros m; induction m
    case zero => simp only [add, ih]
    case succ m' ih' => -- >>> ih ih' ⊢
      unfold add
      rw [ih, ←ih']
      unfold add
      rw [ih]


class Printable (α: Type) where
  print: α → String

instance : Printable nat where
  print n := toString n
    where toString (n: nat) : String :=
      match n with
      | nat.zero => "0"
      | nat.succ n => "S" ++ toString n

instance : Printable String where
  print x := x

#eval Printable.print (nat.succ (nat.succ nat.zero))
#eval Printable.print "Hello, World!"

