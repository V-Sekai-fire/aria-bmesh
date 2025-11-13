# SPDX-License-Identifier: MIT
# Copyright (c) 2025-present K. S. Ernest (iFire) Lee

defmodule AriaBmesh.MixProject do
  use Mix.Project

  def project do
    [
      app: :aria_bmesh,
      version: "0.1.0",
      elixir: "~> 1.18",
      start_permanent: Mix.env() == :prod,
      deps: deps(),
      description: "ARIA BMesh - Topological mesh data structures for n-gon geometry",
      package: package()
    ]
  end

  def application do
    [
      extra_applications: [:logger]
    ]
  end

  defp deps do
    []
  end

  defp package do
    [
      maintainers: ["K. S. Ernest (iFire) Lee"],
      licenses: ["MIT"],
      links: %{"GitHub" => "https://github.com/V-Sekai-fire/aria-bmesh"}
    ]
  end
end
