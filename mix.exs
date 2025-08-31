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
    [
      {:aria_hybrid_planner, git: "https://github.com/V-Sekai-fire/aria-hybrid-planner.git"},
      {:aria_gltf, git: "https://github.com/V-Sekai-fire/aria-character-core.git", sparse: "apps/aria_gltf"},
      {:aria_joint, git: "https://github.com/V-Sekai-fire/aria-character-core.git", sparse: "apps/aria_joint", override: true},
      {:aria_math, git: "https://github.com/V-Sekai-fire/aria-math.git"}
    ]
  end
end
