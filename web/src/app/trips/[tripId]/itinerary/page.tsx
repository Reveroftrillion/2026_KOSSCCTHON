import ItineraryPlanner from '@/components/fe2/ItineraryPlanner'

export default async function ItineraryPage({ params }: PageProps<'/trips/[tripId]/itinerary'>) {
  const { tripId } = await params
  return <ItineraryPlanner tripId={tripId} />
}
