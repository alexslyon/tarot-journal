import SwiftUI
import GRDB

struct ArchetypeHit: Identifiable, Hashable {
    let id: Int64
    let name: String
    let cartomancyType: String?
}

struct ReferenceView: View {
    var body: some View {
        NavigationStack {
            NocturneScreen {
                List(ReferenceGroup.allCases) { group in
                    NavigationLink(value: group) {
                        Label {
                            Text(group.label)
                                .font(TJ.serifFont(17))
                                .foregroundStyle(TJ.text)
                        } icon: {
                            Image(systemName: group.icon)
                                .foregroundStyle(TJ.accent)
                        }
                    }
                    .listRowBackground(TJ.panel)
                }
            }
            .navigationTitle("Reference")
            .navigationDestination(for: ReferenceGroup.self) { group in
                if group == .cards {
                    CardsGroupView()
                } else {
                    ReferenceGroupView(group: group)
                }
            }
            .navigationDestination(for: CardsRoute.self) { route in
                switch route {
                case .byDeckType: DeckTypeListView()
                case .combinations: CombinationsView()
                }
            }
            .navigationDestination(for: DeckTypeSelection.self) { selection in
                TypeArchetypesView(type: selection.type)
            }
            .navigationDestination(for: ArchetypeHit.self) { hit in
                ReferenceDetailView(archetypeId: hit.id,
                                    archetypeName: hit.name)
            }
            .navigationDestination(for: ReferenceEntity.self) { entity in
                EntityDetailView(entity: entity)
            }
        }
    }
}
