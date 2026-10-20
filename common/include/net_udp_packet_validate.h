/*
 * This file is part of the DXX-Rebirth project <https://github.com/dxx-rebirth/dxx-rebirth/>.
 * It is copyright by its individual contributors, as recorded in the
 * project's Git history.  See COPYING.txt at the top level for license terms.
 */
#pragma once

#include <cstddef>
#include <cstdint>
#include <span>

namespace dcx::net_udp_validate {

[[nodiscard]] inline std::uint32_t read_u32_le(const std::span<const std::uint8_t> data, const std::size_t offset) noexcept
{
	return static_cast<std::uint32_t>(data[offset]) |
		(static_cast<std::uint32_t>(data[offset + 1]) << 8) |
		(static_cast<std::uint32_t>(data[offset + 2]) << 16) |
		(static_cast<std::uint32_t>(data[offset + 3]) << 24);
}

[[nodiscard]] inline std::int32_t read_i32_le(const std::span<const std::uint8_t> data, const std::size_t offset) noexcept
{
	return static_cast<std::int32_t>(read_u32_le(data, offset));
}

/* Validate the complete wire shape of an object_data datagram before the
 * stateful object importer sees it.  Sentinel records contain only their
 * nine-byte record header; ordinary object records also contain object_rw.
 */
[[nodiscard]] inline bool object_data(
	const std::span<const std::uint8_t> packet,
	const std::size_t object_rw_size,
	const std::uint32_t object_none,
	const std::uint32_t checksum_marker,
	const std::size_t max_objects,
	const std::size_t max_players) noexcept
{
	constexpr std::size_t packet_header_size = 5;
	constexpr std::size_t record_header_size = 9;
	if (packet.size() < packet_header_size)
		return false;

	const auto nobj = read_i32_le(packet, 1);
	if (nobj < 0)
		return false;

	std::size_t loc = packet_header_size;
	for (std::int32_t i = 0; i < nobj; ++i)
	{
		if (packet.size() - loc < record_header_size)
			return false;
		const auto objnum = read_u32_le(packet, loc);
		const auto owner = static_cast<std::int8_t>(packet[loc + 4]);
		loc += record_header_size;

		if (objnum == object_none)
		{
			if (owner < 0 || static_cast<std::size_t>(owner) >= max_players)
				return false;
			continue;
		}
		if (objnum == checksum_marker)
			continue;

		if (owner < -1 || static_cast<std::size_t>(objnum) >= max_objects)
			return false;
		if (owner >= 0 && static_cast<std::size_t>(owner) >= max_players)
			return false;
		if (packet.size() - loc < object_rw_size)
			return false;
		loc += object_rw_size;
	}
	return loc == packet.size();
}

[[nodiscard]] inline bool endlevel_client(
	const std::span<const std::uint8_t> packet,
	const std::size_t expected_size,
	const std::size_t max_players) noexcept
{
	return packet.size() == expected_size && packet.size() >= 2 &&
		static_cast<std::size_t>(packet[1]) < max_players;
}

} // namespace dcx::net_udp_validate
