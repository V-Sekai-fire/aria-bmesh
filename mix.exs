defmodule AriaBmeshDomain.MixProject do
  use Mix.Project

  def project do
    [
      app: :aria_bmesh_domain,
      version: "0.1.0",
      elixir: "~> 1.17",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  # Run "mix help compile.app" to learn about applications.
  def application do
    [
      extra_applications: [:logger],
      mod: {AriaBmeshDomain.Application, []}
    ]
  end

  # Run "mix help deps" to learn about dependencies.
  defp deps do
    [{:aria_hybrid_planner, git: "https://github.com/V-Sekai-fire/aria-hybrid-planner.git"}]
  end
end
